from __future__ import annotations

from pydantic import BaseModel, Field


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
