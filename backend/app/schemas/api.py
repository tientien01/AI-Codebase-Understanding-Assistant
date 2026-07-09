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


class RepositoryBulkDeleteRequest(BaseModel):
    repository_ids: list[str] = Field(default_factory=list)
    delete_all: bool = False


class RepositoryBulkDeleteResponse(BaseModel):
    deleted_count: int
    repository_ids: list[str] = Field(default_factory=list)


class ImportSessionCreateResponse(BaseModel):
    import_session_id: str
    status: str
    source_type: str


class GitHubImportRequest(BaseModel):
    url: str
    name: str | None = None
    branch: str | None = None


class ImportProjectSummaryDTO(BaseModel):
    suggested_name: str
    source_type: str
    repository_size_bytes: int = 0
    estimated_index_time_seconds: int = 0


class ImportFileStatisticsDTO(BaseModel):
    total_files: int = 0
    supported_files: int = 0
    skipped_files: int = 0
    language_files: dict[str, int] = Field(default_factory=dict)
    python_files: int = 0
    javascript_files: int = 0
    typescript_files: int = 0
    markdown_files: int = 0
    config_files: int = 0


class ImportIgnoreSummaryDTO(BaseModel):
    pattern: str
    skipped_count: int
    reason: str


class ImportSecurityWarningDTO(BaseModel):
    file_path: str
    risk_type: str
    action: str


class ImportDuplicateCandidateDTO(BaseModel):
    repository_id: str
    name: str
    match_reason: str


class ImportActivityLogDTO(BaseModel):
    timestamp: str
    level: str = "info"
    stage: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)


class ImportPreviewResponse(BaseModel):
    import_session_id: str
    status: str
    project_summary: ImportProjectSummaryDTO
    detected_stack: list[str] = Field(default_factory=list)
    file_statistics: ImportFileStatisticsDTO
    folder_preview: list[str] = Field(default_factory=list)
    ignore_summary: list[ImportIgnoreSummaryDTO] = Field(default_factory=list)
    security_warnings: list[ImportSecurityWarningDTO] = Field(default_factory=list)
    indexing_plan: list[str] = Field(default_factory=list)
    possible_duplicates: list[ImportDuplicateCandidateDTO] = Field(default_factory=list)
    activity_logs: list[ImportActivityLogDTO] = Field(default_factory=list)


class ImportConfirmRequest(BaseModel):
    name: str | None = None
    start_indexing: bool = True
    index_profile: str = "balanced"
    duplicate_action: str = "import_as_new"


class ImportConfirmResponse(BaseModel):
    repository_id: str
    indexing_job_id: str | None = None
    status: str
    index_version: int | None = None


class ImportCancelResponse(BaseModel):
    cancelled: bool
    import_session_id: str


class IndexRequest(BaseModel):
    force_reindex: bool = False


class IndexResponse(BaseModel):
    indexing_job_id: str
    repository_id: str
    status: str
    index_version: int = 0


class IndexJobControlResponse(BaseModel):
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


class IndexJobSummaryDTO(BaseModel):
    id: str
    repository_id: str
    status: str
    index_version: int = 0
    total_files: int = 0
    processed_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    started_at: str | None = None
    finished_at: str | None = None


class IndexJobListResponse(BaseModel):
    items: list[IndexJobSummaryDTO]
    next_cursor: str | None = None


class IndexWarningDTO(BaseModel):
    file_path: str | None = None
    warning_type: str = "warning"
    message: str
    line: int | None = None
    severity: str = "warning"


class IndexWarningsResponse(BaseModel):
    items: list[IndexWarningDTO]
    next_cursor: str | None = None


class SkippedFileDTO(BaseModel):
    file_path: str
    reason: str
    matched_pattern: str | None = None


class SkippedFilesResponse(BaseModel):
    items: list[SkippedFileDTO]
    next_cursor: str | None = None


class FailedFileDTO(BaseModel):
    file_path: str
    stage: str
    error_code: str
    message: str
    line: int | None = None


class FailedFilesResponse(BaseModel):
    items: list[FailedFileDTO]
    next_cursor: str | None = None


class StalenessResponse(BaseModel):
    repository_id: str
    is_stale: bool
    current_index_version: int = 0
    last_indexed_at: str | None = None
    stale_reason: str | None = None
    changed_files_count: int = 0
    recommended_action: str | None = None


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


class ReadingPathSignalDTO(BaseModel):
    type: str
    detail: str
    line: int | None = None


class ReadingPathItemDTO(BaseModel):
    rank: int
    file_path: str
    title: str
    reason: str
    confidence: str
    signals: list[ReadingPathSignalDTO] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ReadingPathResponse(BaseModel):
    repository_id: str
    index_version: int = 0
    items: list[ReadingPathItemDTO]


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


class GraphNodeDTO(BaseModel):
    id: str
    type: str
    label: str
    file_path: str | None = None
    coverage: str = "deep_indexed"
    scope_path: str | None = None
    role: str | None = None


class GraphEdgeDTO(BaseModel):
    source: str
    target: str
    type: str
    confidence: float
    evidence_level: str = "deep"


class GraphResponse(BaseModel):
    nodes: list[GraphNodeDTO]
    edges: list[GraphEdgeDTO]


class GraphExpansionRequest(BaseModel):
    scope_path: str


class GraphExpansionResponse(BaseModel):
    job_id: str | None = None
    status: str
    scope_path: str
    message: str


class SearchResultDTO(BaseModel):
    evidence_id: str
    file_path: str
    title: str
    preview: str
    start_line: int
    end_line: int
    score: float
    index_version: int = 0
    is_stale: bool = False


class SearchResponse(BaseModel):
    results: list[SearchResultDTO]


class SymbolDTO(BaseModel):
    symbol_id: str
    file_path: str
    symbol_type: str
    name: str
    start_line: int
    end_line: int
    signature: str = ""
    index_version: int = 0


class SymbolListResponse(BaseModel):
    items: list[SymbolDTO]
    next_cursor: str | None = None


class EndpointListResponse(BaseModel):
    items: list[EndpointDTO]
    next_cursor: str | None = None


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


class SettingsResponse(BaseModel):
    indexing: dict[str, str | int | bool]
    providers: dict[str, str | bool]
    security: dict[str, bool]


class IgnorePatternsResponse(BaseModel):
    default_patterns: list[str]
    user_patterns: list[str] = Field(default_factory=list)
    effective_patterns: list[str]
