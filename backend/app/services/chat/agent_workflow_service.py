from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Callable

from app.schemas.api import CitationDTO
from app.services.chat.tool_registry import ToolExecution, ToolRegistry
from app.services.chat.workflow_contracts import (
    ToolCallStatus,
    ToolInput,
    ToolName,
    ToolObservation,
    WorkflowBudgetUsage,
    WorkflowConfiguration,
    WorkflowDiagnostics,
    WorkflowOutcome,
    WorkflowPlan,
    WorkflowRequest,
    tool_call_id,
)
from app.services.evidence.evidence_service import EvidenceService
from app.services.evidence.selection import EvidenceContextStatus
from app.services.index_models import RepositoryState
from app.services.retrieval.contracts import RetrievalRequest
from app.services.retrieval.retrieval_service import RetrievalService


@dataclass(frozen=True)
class AgentRetrievalPlan:
    question_type: str
    tools: list[str] = field(default_factory=list)
    evidence_limit: int = 5
    workflow_version: str = "assistant/v1"
    configuration_id: str | None = None


@dataclass(frozen=True)
class AgentWorkflowResult:
    question_type: str
    answer: str
    citations: list[CitationDTO]
    evidence_sufficient: bool
    missing_evidence: list[str] = field(default_factory=list)
    plan: AgentRetrievalPlan | None = None
    diagnostics: WorkflowDiagnostics | None = None


class AgentWorkflowService:
    """Deterministic bounded orchestrator over allowlisted typed retrieval tools."""

    def __init__(
        self,
        retrieval: RetrievalService,
        evidence: EvidenceService,
        configuration: WorkflowConfiguration | None = None,
        registry: ToolRegistry | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.retrieval = retrieval
        self.evidence = evidence
        self.configuration = configuration or WorkflowConfiguration(
            context_token_budget=retrieval.ranking_configuration.context_token_budget
        )
        self.registry = registry or ToolRegistry.default(retrieval)
        self.clock = clock

    def answer(
        self,
        repository: RepositoryState,
        message: str,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> AgentWorkflowResult:
        started = self.clock()
        question_type = self.retrieval.classify_question(message)
        workflow_request = WorkflowRequest(
            repository_id=repository.id,
            index_version_id=f"idx_compat_{max(repository.current_index_version, 0)}",
            question=message,
            question_type=question_type,
        )
        typed_plan = self._plan(workflow_request)
        plan = self._compatibility_plan(typed_plan)
        observations: list[ToolObservation] = []
        seen_calls: set[tuple[str, ...]] = set()
        tool_calls_used = 0
        execution: ToolExecution | None = None
        terminal_reason: str | None = None

        for ordinal, tool_name in enumerate(typed_plan.tool_sequence, start=1):
            call_id = tool_call_id(
                workflow_request.request_id,
                self.configuration.config_id,
                tool_name,
                ordinal,
            )
            stop_reason = self._stop_reason(started, tool_calls_used, is_cancelled)
            if stop_reason:
                status = (
                    ToolCallStatus.CANCELLED
                    if stop_reason == "workflow_cancelled"
                    else ToolCallStatus.REJECTED
                )
                observations.append(ToolObservation(call_id, tool_name, status, stop_reason))
                terminal_reason = stop_reason
                break

            tool_input = ToolInput(
                call_id=call_id,
                tool_name=tool_name,
                tool_version="1",
                repository_id=workflow_request.repository_id,
                index_version_id=workflow_request.index_version_id,
                query=workflow_request.question,
                question_type=workflow_request.question_type,
                limit=min(
                    self.configuration.max_candidates_per_tool,
                    self.configuration.max_selected_evidence,
                ),
                round_number=1,
            )
            if tool_input.equivalence_key in seen_calls:
                observations.append(
                    ToolObservation(
                        call_id,
                        tool_name,
                        ToolCallStatus.REJECTED,
                        "equivalent_tool_call_deduplicated",
                    )
                )
                continue
            seen_calls.add(tool_input.equivalence_key)
            tool_calls_used += 1
            try:
                current = self.registry.execute(tool_input, repository)
            except ValueError:
                observations.append(
                    ToolObservation(
                        call_id,
                        tool_name,
                        ToolCallStatus.FAILED,
                        "tool_contract_rejected",
                    )
                )
                return self._terminal_result(
                    plan,
                    WorkflowOutcome.FAILED,
                    ("tool_contract_rejected",),
                    observations,
                    started,
                    tool_calls_used,
                )
            except Exception:
                observations.append(
                    ToolObservation(
                        call_id,
                        tool_name,
                        ToolCallStatus.FAILED,
                        "tool_execution_failed",
                    )
                )
                return self._terminal_result(
                    plan,
                    WorkflowOutcome.FAILED,
                    ("tool_execution_failed",),
                    observations,
                    started,
                    tool_calls_used,
                )
            observations.append(
                ToolObservation(
                    call_id,
                    tool_name,
                    ToolCallStatus.COMPLETED,
                    "tool_completed",
                    current.output,
                )
            )
            execution = current
            post_reason = self._post_tool_stop_reason(started, is_cancelled)
            if post_reason:
                terminal_reason = post_reason
                break
            if current.ranked_candidates:
                break

        if terminal_reason == "workflow_cancelled":
            return self._terminal_result(
                plan,
                WorkflowOutcome.CANCELLED,
                (terminal_reason,),
                observations,
                started,
                tool_calls_used,
            )
        if execution is None:
            return self._terminal_result(
                plan,
                WorkflowOutcome.LIMITED,
                (terminal_reason or "no_tool_executed",),
                observations,
                started,
                tool_calls_used,
            )

        context = self.evidence.select_context(
            repository,
            execution.retrieval_request,
            list(execution.ranked_candidates),
            token_budget=min(
                self.configuration.context_token_budget,
                self.retrieval.ranking_configuration.context_token_budget,
            ),
        )
        citations = self.evidence.context_to_citations(repository, context)
        elapsed_ms = self._elapsed_ms(started)
        if not citations:
            reasons = tuple(
                dict.fromkeys(
                    [
                        *(filter(None, (terminal_reason,))),
                        *(context.missing_requirements or ("no_selected_evidence",)),
                    ]
                )
            )
            diagnostics = self._diagnostics(
                WorkflowOutcome.LIMITED if terminal_reason else WorkflowOutcome.INSUFFICIENT_EVIDENCE,
                reasons,
                observations,
                tool_calls_used,
                context.used_tokens,
                elapsed_ms,
            )
            return AgentWorkflowResult(
                question_type=plan.question_type,
                answer="Chua du bang chung de tra loi chac chan. He thong khong tim thay file, symbol hoac relation phu hop trong index hien tai.",
                citations=[],
                evidence_sufficient=False,
                missing_evidence=list(context.missing_requirements) or ["Expected code or document evidence"],
                plan=plan,
                diagnostics=diagnostics,
            )

        missing = list(
            dict.fromkeys([*context.missing_requirements, *self._missing_evidence(plan, citations)])
        )
        limited = bool(terminal_reason) or context.status != EvidenceContextStatus.READY or bool(missing)
        outcome = WorkflowOutcome.LIMITED if limited else WorkflowOutcome.ANSWERED
        reasons = tuple(
            dict.fromkeys(
                [
                    *(filter(None, (terminal_reason,))),
                    *(missing or ["workflow_completed"]),
                ]
            )
        )
        diagnostics = self._diagnostics(
            outcome,
            reasons,
            observations,
            tool_calls_used,
            context.used_tokens,
            elapsed_ms,
        )
        return AgentWorkflowResult(
            question_type=plan.question_type,
            answer=self.retrieval.generate_grounded_answer(plan.question_type, message, citations),
            citations=citations,
            evidence_sufficient=not limited,
            missing_evidence=missing,
            plan=plan,
            diagnostics=diagnostics,
        )

    def answer_from_citations(
        self,
        repository: RepositoryState,
        message: str,
        citations: list[CitationDTO],
    ) -> AgentWorkflowResult:
        question_type = self.retrieval.classify_question(message)
        request = WorkflowRequest(
            repository.id,
            f"idx_compat_{max(repository.current_index_version, 0)}",
            message,
            question_type,
        )
        typed_plan = self._plan(request)
        plan = self._compatibility_plan(typed_plan)
        missing = self._missing_evidence(plan, citations)
        return AgentWorkflowResult(
            question_type=plan.question_type,
            answer=self.retrieval.generate_grounded_answer(plan.question_type, message, citations),
            citations=citations,
            evidence_sufficient=not missing,
            missing_evidence=missing,
            plan=plan,
        )

    def _plan(self, request: WorkflowRequest) -> WorkflowPlan:
        multi_step_types = {
            "architecture_overview",
            "flow_tracing",
            "impact_analysis",
            "api_question",
            "onboarding",
        }
        if request.question_type in multi_step_types:
            tools = (ToolName.HYBRID_RETRIEVAL,)
        else:
            tools = (ToolName.EXACT_LOOKUP, ToolName.HYBRID_RETRIEVAL)
        return WorkflowPlan(
            workflow_version="assistant/v1",
            configuration_id=self.configuration.config_id,
            request_id=request.request_id,
            question_type=request.question_type,
            tool_sequence=tools,
            evidence_limit=self.configuration.max_selected_evidence,
        )

    @staticmethod
    def _compatibility_plan(plan: WorkflowPlan) -> AgentRetrievalPlan:
        return AgentRetrievalPlan(
            question_type=plan.question_type,
            tools=[item.value for item in plan.tool_sequence],
            evidence_limit=plan.evidence_limit,
            workflow_version=plan.workflow_version,
            configuration_id=plan.configuration_id,
        )

    def _stop_reason(
        self,
        started: float,
        tool_calls_used: int,
        is_cancelled: Callable[[], bool] | None,
    ) -> str | None:
        if is_cancelled and is_cancelled():
            return "workflow_cancelled"
        if self._elapsed_ms(started) >= self.configuration.max_elapsed_ms:
            return "elapsed_time_budget_exhausted"
        if tool_calls_used >= self.configuration.max_tool_calls:
            return "tool_call_budget_exhausted"
        return None

    def _post_tool_stop_reason(
        self,
        started: float,
        is_cancelled: Callable[[], bool] | None,
    ) -> str | None:
        if is_cancelled and is_cancelled():
            return "workflow_cancelled"
        if self._elapsed_ms(started) >= self.configuration.max_elapsed_ms:
            return "elapsed_time_budget_exhausted"
        return None

    def _elapsed_ms(self, started: float) -> int:
        return max(0, int((self.clock() - started) * 1_000))

    def _diagnostics(
        self,
        outcome: WorkflowOutcome,
        reasons: tuple[str, ...],
        observations: list[ToolObservation],
        tool_calls_used: int,
        context_tokens_used: int,
        elapsed_ms: int,
    ) -> WorkflowDiagnostics:
        return WorkflowDiagnostics(
            outcome=outcome,
            reason_codes=reasons,
            observations=tuple(observations),
            budget=WorkflowBudgetUsage(
                rounds_used=1 if tool_calls_used else 0,
                tool_calls_used=tool_calls_used,
                context_tokens_used=context_tokens_used,
                elapsed_ms=elapsed_ms,
            ),
        )

    def _terminal_result(
        self,
        plan: AgentRetrievalPlan,
        outcome: WorkflowOutcome,
        reasons: tuple[str, ...],
        observations: list[ToolObservation],
        started: float,
        tool_calls_used: int,
    ) -> AgentWorkflowResult:
        diagnostics = self._diagnostics(
            outcome,
            reasons,
            observations,
            tool_calls_used,
            0,
            self._elapsed_ms(started),
        )
        return AgentWorkflowResult(
            question_type=plan.question_type,
            answer="Yeu cau khong the tiep tuc trong gioi han workflow hien tai.",
            citations=[],
            evidence_sufficient=False,
            missing_evidence=list(reasons),
            plan=plan,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _missing_evidence(plan: AgentRetrievalPlan, citations: list[CitationDTO]) -> list[str]:
        if not citations:
            return ["Expected at least one citation"]
        if plan.question_type in {"flow_tracing", "api_question", "impact_analysis"} and len(citations) < 2:
            return ["Expected multiple citations for multi-step codebase reasoning"]
        return []
