from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    options: dict[str, int] = Field(default_factory=dict)


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
