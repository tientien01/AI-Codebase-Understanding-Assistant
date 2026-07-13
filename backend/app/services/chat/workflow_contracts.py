from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from math import isfinite


CONTROLLED_QUESTION_TYPES = frozenset(
    {
        "architecture_overview",
        "flow_tracing",
        "api_question",
        "database_question",
        "debugging",
        "onboarding",
        "impact_analysis",
        "code_question",
    }
)


class WorkflowOutcome(str, Enum):
    ANSWERED = "answered"
    LIMITED = "limited"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ToolName(str, Enum):
    EXACT_LOOKUP = "exact_lookup"
    HYBRID_RETRIEVAL = "hybrid_retrieval"


class ToolCallStatus(str, Enum):
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class WorkflowConfiguration:
    max_rounds: int = 1
    max_tool_calls: int = 2
    max_candidates_per_tool: int = 6
    max_selected_evidence: int = 6
    context_token_budget: int = 8_000
    max_elapsed_ms: int = 10_000
    max_provider_calls: int = 0
    max_provider_cost: float = 0.0
    schema_version: str = "assistant-config/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "assistant-config/v1":
            raise ValueError("unsupported assistant configuration schema")
        positive = (
            self.max_rounds,
            self.max_tool_calls,
            self.max_candidates_per_tool,
            self.max_selected_evidence,
            self.context_token_budget,
            self.max_elapsed_ms,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("assistant workflow budgets must be positive")
        if self.max_provider_calls < 0:
            raise ValueError("assistant provider-call budget must be non-negative")
        if not isfinite(self.max_provider_cost) or self.max_provider_cost < 0:
            raise ValueError("assistant provider-cost budget must be finite and non-negative")

    @property
    def config_id(self) -> str:
        digest = hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()[:24]
        return f"agentcfg_{digest}"

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=True, separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True)
class WorkflowRequest:
    repository_id: str
    index_version_id: str
    question: str
    question_type: str
    schema_version: str = "assistant-request/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "assistant-request/v1":
            raise ValueError("unsupported assistant request schema")
        if not self.repository_id.strip() or not self.index_version_id.startswith("idx_"):
            raise ValueError("assistant request ownership is required")
        if not self.question.strip() or self.question_type not in CONTROLLED_QUESTION_TYPES:
            raise ValueError("assistant question and controlled type are required")

    @property
    def request_id(self) -> str:
        payload = "|".join(
            (self.repository_id, self.index_version_id, self.question_type, self.question.strip())
        )
        return f"agentreq_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


@dataclass(frozen=True)
class ToolInput:
    call_id: str
    tool_name: ToolName
    tool_version: str
    repository_id: str
    index_version_id: str
    query: str
    question_type: str
    limit: int
    round_number: int
    schema_version: str = "assistant-tool-input/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "assistant-tool-input/v1":
            raise ValueError("unsupported assistant tool-input schema")
        if not self.call_id.startswith("toolcall_"):
            raise ValueError("tool call identity must use the toolcall_ prefix")
        if not isinstance(self.tool_name, ToolName) or self.tool_version != "1":
            raise ValueError("tool name and version must be controlled")
        if not self.repository_id.strip() or not self.index_version_id.startswith("idx_"):
            raise ValueError("tool input ownership is required")
        if not self.query.strip() or self.question_type not in CONTROLLED_QUESTION_TYPES:
            raise ValueError("tool query and question type are required")
        if self.limit <= 0 or self.round_number <= 0:
            raise ValueError("tool limit and round must be positive")

    @property
    def equivalence_key(self) -> tuple[str, ...]:
        return (
            self.tool_name.value,
            self.tool_version,
            self.repository_id,
            self.index_version_id,
            " ".join(self.query.lower().split()),
            self.question_type,
            str(self.limit),
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["tool_name"] = self.tool_name.value
        return payload


@dataclass(frozen=True)
class ToolOutput:
    call_id: str
    tool_name: ToolName
    tool_version: str
    repository_id: str
    index_version_id: str
    candidate_ids: tuple[str, ...]
    coverage: str
    truncated: bool
    diagnostics: tuple[str, ...]
    duration_ms: int
    retryable: bool
    schema_version: str = "assistant-tool-output/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "assistant-tool-output/v1":
            raise ValueError("unsupported assistant tool-output schema")
        if not isinstance(self.tool_name, ToolName) or self.tool_version != "1":
            raise ValueError("tool output name and version must be controlled")
        if not self.repository_id.strip() or not self.index_version_id.startswith("idx_"):
            raise ValueError("tool output ownership is required")
        if self.duration_ms < 0 or not self.coverage.strip():
            raise ValueError("tool output duration and coverage are invalid")
        if any(not item.startswith("cand_") for item in self.candidate_ids):
            raise ValueError("tool output candidate identities are invalid")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["tool_name"] = self.tool_name.value
        return payload


@dataclass(frozen=True)
class ToolObservation:
    call_id: str
    tool_name: ToolName
    status: ToolCallStatus
    reason_code: str
    output: ToolOutput | None = None

    def __post_init__(self) -> None:
        if not self.call_id.startswith("toolcall_") or not isinstance(self.tool_name, ToolName):
            raise ValueError("tool observation identity is invalid")
        if not isinstance(self.status, ToolCallStatus) or not self.reason_code.strip():
            raise ValueError("tool observation status and reason are required")


@dataclass(frozen=True)
class WorkflowPlan:
    workflow_version: str
    configuration_id: str
    request_id: str
    question_type: str
    tool_sequence: tuple[ToolName, ...]
    evidence_limit: int

    def __post_init__(self) -> None:
        if self.workflow_version != "assistant/v1":
            raise ValueError("unsupported assistant workflow version")
        if not self.configuration_id.startswith("agentcfg_"):
            raise ValueError("workflow configuration identity is invalid")
        if (
            not self.request_id.startswith("agentreq_")
            or self.evidence_limit <= 0
            or self.question_type not in CONTROLLED_QUESTION_TYPES
        ):
            raise ValueError("workflow request identity and evidence limit are required")
        if not self.tool_sequence or any(not isinstance(item, ToolName) for item in self.tool_sequence):
            raise ValueError("workflow plan requires controlled tools")


@dataclass(frozen=True)
class WorkflowBudgetUsage:
    rounds_used: int
    tool_calls_used: int
    context_tokens_used: int
    elapsed_ms: int
    provider_calls_used: int = 0
    provider_cost: float = 0.0

    def __post_init__(self) -> None:
        values = (
            self.rounds_used,
            self.tool_calls_used,
            self.context_tokens_used,
            self.elapsed_ms,
            self.provider_calls_used,
        )
        if any(value < 0 for value in values) or not isfinite(self.provider_cost) or self.provider_cost < 0:
            raise ValueError("workflow budget usage must be finite and non-negative")


@dataclass(frozen=True)
class WorkflowDiagnostics:
    outcome: WorkflowOutcome
    reason_codes: tuple[str, ...]
    observations: tuple[ToolObservation, ...]
    budget: WorkflowBudgetUsage

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, WorkflowOutcome):
            raise ValueError("workflow outcome must be controlled")
        if not self.reason_codes or any(not reason.strip() for reason in self.reason_codes):
            raise ValueError("workflow diagnostics require reason codes")


def tool_call_id(request_id: str, config_id: str, tool_name: ToolName, ordinal: int) -> str:
    payload = f"{request_id}|{config_id}|{tool_name.value}|{ordinal}"
    return f"toolcall_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"
