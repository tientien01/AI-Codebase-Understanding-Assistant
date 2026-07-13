from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.api import CitationDTO
from app.services.evidence.evidence_service import EvidenceService
from app.services.evidence.selection import EvidenceContextStatus
from app.services.index_models import RepositoryState
from app.services.retrieval.retrieval_service import RetrievalService


@dataclass(frozen=True)
class AgentRetrievalPlan:
    question_type: str
    tools: list[str] = field(default_factory=list)
    evidence_limit: int = 5


@dataclass(frozen=True)
class AgentWorkflowResult:
    question_type: str
    answer: str
    citations: list[CitationDTO]
    evidence_sufficient: bool
    missing_evidence: list[str] = field(default_factory=list)
    plan: AgentRetrievalPlan | None = None


class AgentWorkflowService:
    """Deterministic agent workflow for planning, retrieval, verification, and fallback answers."""

    def __init__(self, retrieval: RetrievalService, evidence: EvidenceService) -> None:
        self.retrieval = retrieval
        self.evidence = evidence

    def answer(self, repository: RepositoryState, message: str) -> AgentWorkflowResult:
        plan = self._plan(message)
        request, ranked_candidates = self.retrieval.ranked_search(
            repository, message, limit=plan.evidence_limit
        )
        context = self.evidence.select_context(
            repository,
            request,
            ranked_candidates,
            token_budget=self.retrieval.ranking_configuration.context_token_budget,
        )
        citations = self.evidence.context_to_citations(repository, context)
        if not citations:
            return AgentWorkflowResult(
                question_type=plan.question_type,
                answer="Chua du bang chung de tra loi chac chan. He thong khong tim thay file, symbol hoac relation phu hop trong index hien tai.",
                citations=[],
                evidence_sufficient=False,
                missing_evidence=(
                    list(context.missing_requirements)
                    or ["Expected code or document evidence", "Expected citation metadata"]
                ),
                plan=plan,
            )

        missing = list(dict.fromkeys([*context.missing_requirements, *self._missing_evidence(plan, citations)]))
        evidence_sufficient = context.status != EvidenceContextStatus.INSUFFICIENT and not missing
        return AgentWorkflowResult(
            question_type=plan.question_type,
            answer=self.retrieval.generate_grounded_answer(plan.question_type, message, citations),
            citations=citations,
            evidence_sufficient=evidence_sufficient,
            missing_evidence=missing,
            plan=plan,
        )

    def answer_from_citations(
        self,
        repository: RepositoryState,
        message: str,
        citations: list[CitationDTO],
    ) -> AgentWorkflowResult:
        plan = self._plan(message)
        missing = self._missing_evidence(plan, citations)
        return AgentWorkflowResult(
            question_type=plan.question_type,
            answer=self.retrieval.generate_grounded_answer(plan.question_type, message, citations),
            citations=citations,
            evidence_sufficient=not missing,
            missing_evidence=missing,
            plan=plan,
        )

    def _plan(self, message: str) -> AgentRetrievalPlan:
        question_type = self.retrieval.classify_question(message)
        tools = ["hybrid_search", "semantic_vector"]
        if question_type in {"flow_tracing", "impact_analysis", "api_question"}:
            tools.append("graph_context")
        if question_type in {"architecture_overview", "onboarding"}:
            tools.append("semantic_summary")
        return AgentRetrievalPlan(question_type=question_type, tools=tools, evidence_limit=6)

    def _missing_evidence(self, plan: AgentRetrievalPlan, citations: list[CitationDTO]) -> list[str]:
        if not citations:
            return ["Expected at least one citation"]
        if plan.question_type in {"flow_tracing", "api_question", "impact_analysis"} and len(citations) < 2:
            return ["Expected multiple citations for multi-step codebase reasoning"]
        return []
