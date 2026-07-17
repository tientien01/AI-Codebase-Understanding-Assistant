from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AssistantPage = Literal[
    "overview",
    "code",
    "graph",
    "api",
    "assistant",
    "impact",
    "search",
    "evidence",
    "evaluation",
]


class AssistantRequestContext(BaseModel):
    """Bounded workspace identifiers; source content never crosses this boundary."""

    model_config = ConfigDict(extra="forbid")

    page: AssistantPage
    file_path: str | None = Field(default=None, min_length=1, max_length=1_024)
    start_line: int | None = Field(default=None, ge=1, le=1_000_000)
    end_line: int | None = Field(default=None, ge=1, le=1_000_000)
    symbol_name: str | None = Field(default=None, min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_shape(self) -> AssistantRequestContext:
        has_source_details = any(
            value is not None
            for value in (self.file_path, self.start_line, self.end_line, self.symbol_name)
        )
        if self.page != "code" and has_source_details:
            raise ValueError("source context is only valid for the code page")
        if self.page == "code" and self.file_path is None:
            raise ValueError("code context requires file_path")
        if (self.start_line is None) != (self.end_line is None):
            raise ValueError("start_line and end_line must be supplied together")
        if self.start_line is not None and self.end_line is not None and self.end_line < self.start_line:
            raise ValueError("end_line must not precede start_line")
        if self.file_path is not None:
            path = PurePosixPath(self.file_path)
            if (
                "\\" in self.file_path
                or path.is_absolute()
                or self.file_path != path.as_posix()
                or any(part in {"", ".", ".."} for part in path.parts)
            ):
                raise ValueError("file_path must be a canonical repository-relative path")
        return self


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(
        default=None, min_length=14, max_length=128, pattern=r"^conversation_[A-Za-z0-9_-]+$"
    )
    message: str = Field(min_length=1, max_length=16_000)
    options: dict[str, int] = Field(default_factory=dict)
    context: AssistantRequestContext | None = None


class SearchAskWithEvidenceRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    evidence_ids: list[str] = Field(default_factory=list)


class CitationDTO(BaseModel):
    evidence_id: str
    file_path: str
    symbol_name: str | None = None
    start_line: int
    end_line: int
    index_version: int = 0
    is_stale: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    question_type: str
    answer: str
    citations: list[CitationDTO]
    evidence_sufficient: bool
    missing_evidence: list[str] = Field(default_factory=list)
    generation_mode: Literal["deterministic", "ollama", "provider", "deterministic_fallback"] = "deterministic"
    provider_state: Literal["ready", "degraded", "unavailable"] = "unavailable"
    retrieval_mode: Literal["sparse", "hybrid"] = "sparse"


class ConversationMessageDTO(BaseModel):
    message_id: str
    role: Literal["user", "assistant"]
    content: str
    index_version: int
    created_at: str
    citations: list[CitationDTO] = Field(default_factory=list)
    evidence_sufficient: bool | None = None


class ConversationSummaryDTO(BaseModel):
    conversation_id: str
    title: str | None = None
    status: str
    message_count: int
    latest_index_version: int
    is_stale: bool
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    items: list[ConversationSummaryDTO]


class ConversationTranscriptResponse(BaseModel):
    conversation: ConversationSummaryDTO
    messages: list[ConversationMessageDTO]


class EvidenceDTO(BaseModel):
    evidence_id: str
    repository_id: str
    index_version: int = 0
    source_type: str
    file_path: str
    symbol_name: str | None = None
    start_line: int
    end_line: int
    content_preview: str
    relevance_reason: str
    confidence_score: float
    retrieval_source: str
    is_stale: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class EvidenceValidationRequest(BaseModel):
    evidence_ids: list[str] = Field(default_factory=list)


class EvidenceValidationItemDTO(BaseModel):
    evidence_id: str
    is_valid: bool
    is_stale: bool = False
    reason: str | None = None


class EvidenceValidationResponse(BaseModel):
    items: list[EvidenceValidationItemDTO]
