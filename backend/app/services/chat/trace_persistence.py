"""Privacy-safe persistence contracts for completed assistant turns."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
import hashlib
import json
import re
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

from app.schemas.api import ChatResponse, CitationDTO

if TYPE_CHECKING:
    from app.services.chat.agent_workflow_service import AgentWorkflowResult
    from app.services.chat.conversation_memory import ConversationMemoryProjection


MAX_PERSISTED_MESSAGE_CHARS = 16_000
REDACTION_MARKER = "[REDACTED]"
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(bearer\s+)[a-z0-9._~+/=-]{8,}"),
    re.compile(r"\b(?:sk[-_]|ghp_|github_pat_)[A-Za-z0-9_-]{8,}\b"),
    re.compile(
        r"(?i)\b(password|passwd|api[_-]?key|access[_-]?token|secret)\b"
        r"(\s*[:=]\s*)([^\s,;]+)"
    ),
)


def redact_message(value: str) -> str:
    """Bound message storage and remove common credential-shaped values."""

    result = value[:MAX_PERSISTED_MESSAGE_CHARS]
    result = _SECRET_PATTERNS[0].sub(lambda match: f"{match.group(1)}{REDACTION_MARKER}", result)
    result = _SECRET_PATTERNS[1].sub(REDACTION_MARKER, result)
    result = _SECRET_PATTERNS[2].sub(
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTION_MARKER}", result
    )
    return result


class TraceEventType(str, Enum):
    QUESTION_CLASSIFIED = "question_classified"
    PLAN_CREATED = "plan_created"
    TOOL_COMPLETED = "tool_completed"
    TOOL_REJECTED = "tool_rejected"
    TOOL_FAILED = "tool_failed"
    TOOL_CANCELLED = "tool_cancelled"
    SUFFICIENCY_DECIDED = "sufficiency_decided"
    ANSWER_VALIDATED = "answer_validated"
    WORKFLOW_COMPLETED = "workflow_completed"


_EVENT_PAYLOAD_KEYS = {
    TraceEventType.QUESTION_CLASSIFIED: {"question_type"},
    TraceEventType.PLAN_CREATED: {"configuration_id", "tools", "evidence_limit"},
    TraceEventType.TOOL_COMPLETED: {
        "call_id", "reason_code", "candidate_ids", "coverage", "truncated"
    },
    TraceEventType.TOOL_REJECTED: {
        "call_id", "reason_code", "candidate_ids", "coverage", "truncated"
    },
    TraceEventType.TOOL_FAILED: {
        "call_id", "reason_code", "candidate_ids", "coverage", "truncated"
    },
    TraceEventType.TOOL_CANCELLED: {
        "call_id", "reason_code", "candidate_ids", "coverage", "truncated"
    },
    TraceEventType.SUFFICIENCY_DECIDED: {
        "action", "reason_code", "missing_requirements", "coverage"
    },
    TraceEventType.ANSWER_VALIDATED: {
        "citation_ids", "citation_count", "validation_valid", "provider_accepted"
    },
    TraceEventType.WORKFLOW_COMPLETED: {"outcome", "missing_requirements"},
}


@dataclass(frozen=True)
class TraceEventRecord:
    event_id: str
    sequence: int
    event_type: TraceEventType
    status: str
    payload_json: str
    tool_name: str | None = None
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.event_id.startswith("traceevent_") or self.sequence <= 0:
            raise ValueError("trace event identity and sequence are invalid")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("trace event duration cannot be negative")
        payload = json.loads(self.payload_json)
        if not isinstance(payload, dict):
            raise ValueError("trace event payload must be an object")
        if not set(payload).issubset(_EVENT_PAYLOAD_KEYS[self.event_type]):
            raise ValueError("trace event payload contains non-allowlisted fields")
        if redact_message(self.payload_json) != self.payload_json:
            raise ValueError("trace event payload contains credential-shaped content")

    @property
    def payload(self) -> dict[str, object]:
        return json.loads(self.payload_json)


@dataclass(frozen=True)
class PersistedClaim:
    claim_id: str
    text: str
    support_level: str
    citation_ids: tuple[str, ...]


@dataclass(frozen=True)
class PersistedAssistantTurn:
    trace_id: str
    conversation_id: str
    request_message_id: str
    response_message_id: str
    repository_id: str
    index_version: int
    operator_message: str
    assistant_message: str
    outcome: str
    question_type: str
    workflow_version: str
    configuration_id: str | None
    budget_json: str
    claims: tuple[PersistedClaim, ...]
    citations: tuple[CitationDTO, ...]
    events: tuple[TraceEventRecord, ...]
    started_at: datetime
    finished_at: datetime

    def __post_init__(self) -> None:
        prefixes = (
            (self.trace_id, "trace_"),
            (self.conversation_id, "conversation_"),
            (self.request_message_id, "message_"),
            (self.response_message_id, "message_"),
        )
        if any(not value.startswith(prefix) for value, prefix in prefixes):
            raise ValueError("persisted assistant identities are invalid")
        if not self.repository_id or self.index_version <= 0:
            raise ValueError("persisted assistant ownership is required")
        messages = (self.operator_message, self.assistant_message, *(claim.text for claim in self.claims))
        if any(len(message) > MAX_PERSISTED_MESSAGE_CHARS for message in messages):
            raise ValueError("persisted assistant message exceeds the storage bound")
        if any(redact_message(message) != message for message in messages):
            raise ValueError("persisted assistant message contains credential-shaped content")
        if tuple(event.sequence for event in self.events) != tuple(range(1, len(self.events) + 1)):
            raise ValueError("trace events must be contiguous and ordered")


@dataclass(frozen=True)
class AssistantTraceReplay:
    turn: PersistedAssistantTurn


class AssistantTraceStorePort(Protocol):
    def save_assistant_turn(self, turn: PersistedAssistantTurn) -> None: ...

    def get_agent_trace(
        self, repository_id: str, trace_id: str
    ) -> AssistantTraceReplay | None: ...


def _payload(**values: object) -> str:
    """Serialize only bounded scalar and string-list metadata chosen by this module."""

    safe: dict[str, object] = {}
    for key, value in values.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value[:256] if isinstance(value, str) else value
        elif isinstance(value, (tuple, list)):
            safe[key] = [str(item)[:128] for item in value[:32]]
        else:
            raise ValueError(f"unsupported trace payload value for {key}")
    return json.dumps(safe, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _identity(prefix: str) -> str:
    return f"{prefix}{uuid4().hex}"


def normalize_conversation_id(value: str | None, repository_id: str | None = None) -> str:
    if value and value.startswith("conversation_") and len(value) <= 128:
        return value
    if value:
        digest = hashlib.sha256(f"{repository_id or ''}|{value}".encode("utf-8")).hexdigest()[:32]
        return f"conversation_{digest}"
    return _identity("conversation_")


def build_persisted_turn(
    repository_id: str,
    index_version: int,
    operator_message: str,
    response: ChatResponse,
    result: AgentWorkflowResult | None,
    *,
    provider_accepted: bool = False,
    memory: ConversationMemoryProjection | None = None,
) -> PersistedAssistantTurn:
    trace_id = _identity("trace_")
    request_message_id = _identity("message_")
    events: list[TraceEventRecord] = []

    def add(
        event_type: TraceEventType,
        status: str,
        *,
        tool_name: str | None = None,
        duration_ms: int | None = None,
        **payload: object,
    ) -> None:
        sequence = len(events) + 1
        events.append(
            TraceEventRecord(
                event_id=_identity("traceevent_"),
                sequence=sequence,
                event_type=event_type,
                status=status,
                payload_json=_payload(**payload),
                tool_name=tool_name,
                duration_ms=duration_ms,
            )
        )

    add(TraceEventType.QUESTION_CLASSIFIED, "completed", question_type=response.question_type)
    if result and result.plan:
        add(
            TraceEventType.PLAN_CREATED,
            "completed",
            configuration_id=result.plan.configuration_id,
            tools=result.plan.tools,
            evidence_limit=result.plan.evidence_limit,
        )
    if result and result.diagnostics:
        for observation in result.diagnostics.observations:
            status = observation.status.value
            event_type = {
                "completed": TraceEventType.TOOL_COMPLETED,
                "rejected": TraceEventType.TOOL_REJECTED,
                "failed": TraceEventType.TOOL_FAILED,
                "cancelled": TraceEventType.TOOL_CANCELLED,
            }[status]
            output = observation.output
            add(
                event_type,
                status,
                tool_name=observation.tool_name.value,
                duration_ms=output.duration_ms if output else None,
                call_id=observation.call_id,
                reason_code=observation.reason_code,
                candidate_ids=output.candidate_ids if output else (),
                coverage=output.coverage if output else None,
                truncated=output.truncated if output else False,
            )
    if result and result.sufficiency:
        add(
            TraceEventType.SUFFICIENCY_DECIDED,
            "completed",
            action=result.sufficiency.action.value,
            reason_code=result.sufficiency.reason_code,
            missing_requirements=result.sufficiency.missing_requirements,
            coverage=result.sufficiency.coverage,
        )
    validation = result.citation_validation if result else None
    add(
        TraceEventType.ANSWER_VALIDATED,
        "completed" if response.evidence_sufficient else "limited",
        citation_ids=tuple(citation.evidence_id for citation in response.citations),
        citation_count=len(response.citations),
        validation_valid=bool(validation and validation.valid),
        provider_accepted=provider_accepted,
    )
    outcome = (
        result.diagnostics.outcome.value
        if result and result.diagnostics
        else ("answered" if response.evidence_sufficient else "insufficient_evidence")
    )
    add(
        TraceEventType.WORKFLOW_COMPLETED,
        "completed",
        outcome=outcome,
        missing_requirements=tuple(response.missing_evidence),
    )
    budget = result.diagnostics.budget if result and result.diagnostics else None
    budget_json = _payload(
        rounds_used=budget.rounds_used if budget else 0,
        tool_calls_used=budget.tool_calls_used if budget else 0,
        context_tokens_used=budget.context_tokens_used if budget else 0,
        elapsed_ms=budget.elapsed_ms if budget else 0,
        provider_calls_used=1 if provider_accepted else 0,
        provider_cost=budget.provider_cost if budget else 0.0,
        memory_messages_used=memory.messages_used if memory else 0,
        memory_tokens_used=memory.tokens_used if memory else 0,
        memory_token_budget=memory.token_budget if memory else 0,
        memory_truncated=memory.truncated if memory else False,
        memory_stale_history=memory.stale_history if memory else False,
    )
    citation_ids = tuple(citation.evidence_id for citation in response.citations)
    support_level = "supported" if response.evidence_sufficient else (
        "qualified" if citation_ids else "unsupported"
    )
    claim = PersistedClaim(
        claim_id=_identity("claim_"),
        text=redact_message(response.answer),
        support_level=support_level,
        citation_ids=citation_ids,
    )
    now = datetime.now(UTC)
    return PersistedAssistantTurn(
        trace_id=trace_id,
        conversation_id=normalize_conversation_id(response.conversation_id, repository_id),
        request_message_id=request_message_id,
        response_message_id=response.message_id,
        repository_id=repository_id,
        index_version=index_version,
        operator_message=redact_message(operator_message),
        assistant_message=redact_message(response.answer),
        outcome=outcome,
        question_type=response.question_type,
        workflow_version=result.plan.workflow_version if result and result.plan else "assistant/v1",
        configuration_id=result.plan.configuration_id if result and result.plan else None,
        budget_json=budget_json,
        claims=(claim,),
        citations=tuple(response.citations),
        events=tuple(events),
        started_at=now,
        finished_at=now,
    )
