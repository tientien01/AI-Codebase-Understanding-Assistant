from __future__ import annotations

from app.core.errors import DomainError
from app.schemas.api import (
    FailedFileDTO,
    FailedFilesResponse,
    IndexJobListResponse,
    IndexJobSummaryDTO,
    IndexWarningsResponse,
    IndexWarningDTO,
    SkippedFileDTO,
    SkippedFilesResponse,
)
from app.services.index_models import IndexingJobRecord
from app.services.repositories.repository_service import RepositoryService
from app.services.repositories.repository_store import RepositoryStore


class IndexingJobService:
    def __init__(self, store: RepositoryStore, repositories: RepositoryService) -> None:
        self.store = store
        self.repositories = repositories

    def list_indexing_jobs(self, repository_id: str) -> IndexJobListResponse:
        repository = self.repositories.get_repository(repository_id)
        jobs = self.store.list_indexing_jobs(repository.id)
        return IndexJobListResponse(
            items=[
                IndexJobSummaryDTO(
                    id=job.id,
                    repository_id=job.repository_id,
                    status=job.status,
                    index_version=job.index_version,
                    total_files=job.total_files,
                    processed_files=job.processed_files,
                    skipped_files=job.skipped_files,
                    failed_files=job.failed_files,
                    started_at=job.started_at,
                    finished_at=job.finished_at,
                )
                for job in jobs
            ]
        )

    def get_index_warnings(self, repository_id: str, job_id: str) -> IndexWarningsResponse:
        job = self.get_indexing_job(repository_id, job_id)
        return IndexWarningsResponse(items=[IndexWarningDTO(message=warning) for warning in job.warnings])

    def get_skipped_files(self, repository_id: str, job_id: str) -> SkippedFilesResponse:
        job = self.get_indexing_job(repository_id, job_id)
        return SkippedFilesResponse(
            items=[
                SkippedFileDTO(
                    file_path=str(item.get("file_path") or ""),
                    reason=str(item.get("reason") or "skipped"),
                    matched_pattern=item.get("matched_pattern"),
                )
                for item in job.skipped_file_records
            ]
        )

    def get_failed_files(self, repository_id: str, job_id: str) -> FailedFilesResponse:
        job = self.get_indexing_job(repository_id, job_id)
        return FailedFilesResponse(
            items=[
                FailedFileDTO(
                    file_path=str(item.get("file_path") or ""),
                    stage=str(item.get("stage") or "unknown"),
                    error_code=str(item.get("error_code") or "ERROR"),
                    message=str(item.get("message") or "File failed during indexing."),
                    line=item.get("line") if isinstance(item.get("line"), int) else None,
                )
                for item in job.failed_file_records
            ]
        )

    def get_indexing_job(self, repository_id: str, job_id: str) -> IndexingJobRecord:
        self.repositories.get_repository(repository_id)
        job = self.store.get_indexing_job(repository_id, job_id)
        if job is None:
            raise DomainError("INDEXING_JOB_NOT_FOUND", "Indexing job not found.", 404, {"job_id": job_id})
        return job
