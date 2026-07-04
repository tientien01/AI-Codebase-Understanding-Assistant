from __future__ import annotations

from pydantic import BaseModel, Field


class RepositoryDTO(BaseModel):
    id: str
    name: str
    source_type: str
    source_label: str | None = None
    source_uri: str | None = None
    status: str
    current_index_version: int = 0
    detected_stack: list[str] = Field(default_factory=list)
    total_files: int = 0
    indexed_files: int = 0
    symbols: int = 0
    endpoints: int = 0
    chunks: int = 0
    graph_nodes: int = 0
    last_indexed_at: str | None = None


class RepositoryCreateResponse(BaseModel):
    repository_id: str
    name: str
    status: str
    source_type: str


class RepositoryDeleteResponse(BaseModel):
    deleted: bool
    repository_id: str


class IndexRequest(BaseModel):
    force_reindex: bool = False


class IndexResponse(BaseModel):
    indexing_job_id: str
    repository_id: str
    status: str
    index_version: int = 0


class IndexStatusResponse(BaseModel):
    repository_id: str
    job_id: str | None = None
    status: str
    current_step: str
    index_version: int = 0
    total_files: int
    processed_files: int
    skipped_files: int = 0
    failed_files: int
    progress: int
    stats: dict[str, int] = Field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    logs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class ImportantFileDTO(BaseModel):
    file_path: str
    reason: str


class ModuleDTO(BaseModel):
    name: str
    summary: str
    file_count: int = 0


class EndpointDTO(BaseModel):
    method: str
    path: str
    handler: str
    file_path: str
    start_line: int
    end_line: int


class OverviewResponse(BaseModel):
    repository_id: str
    name: str
    detected_stack: list[str]
    important_files: list[ImportantFileDTO]
    modules: list[ModuleDTO]
    endpoints: list[EndpointDTO]
    documentation_gaps: list[str]
    stats: dict[str, int]


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    options: dict[str, int] = Field(default_factory=dict)


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


class GraphNodeDTO(BaseModel):
    id: str
    type: str
    label: str
    file_path: str | None = None


class GraphEdgeDTO(BaseModel):
    source: str
    target: str
    type: str
    confidence: float


class GraphResponse(BaseModel):
    nodes: list[GraphNodeDTO]
    edges: list[GraphEdgeDTO]


class SearchResultDTO(BaseModel):
    evidence_id: str
    file_path: str
    title: str
    preview: str
    start_line: int
    end_line: int
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResultDTO]


class FileTreeNodeDTO(BaseModel):
    name: str
    path: str
    type: str
    children: list["FileTreeNodeDTO"] = Field(default_factory=list)


class FileContentResponse(BaseModel):
    file_path: str
    language: str
    content: str
    lines: list[str]
    symbols: list[CitationDTO] = Field(default_factory=list)
