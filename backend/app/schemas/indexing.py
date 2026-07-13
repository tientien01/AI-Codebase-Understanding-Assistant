from __future__ import annotations

from pydantic import BaseModel, Field


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
