from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import require_api_auth
from app.schemas.indexing import (
    FailedFilesResponse,
    IndexJobControlResponse,
    IndexJobListResponse,
    IndexRequest,
    IndexResponse,
    IndexStatusResponse,
    IndexWarningsResponse,
    SkippedFilesResponse,
    StalenessResponse,
)
from app.services.codebase_service import codebase_service


router = APIRouter(prefix="/repositories", tags=["repositories"], dependencies=[Depends(require_api_auth)])


@router.post("/{repository_id}/index", response_model=IndexResponse)
def start_indexing(repository_id: str, request: IndexRequest | None = None) -> IndexResponse:
    result = codebase_service.start_indexing_background(repository_id, request.force_reindex if request else False)
    return IndexResponse(**result)


@router.get("/{repository_id}/index/status", response_model=IndexStatusResponse)
def get_index_status(repository_id: str) -> IndexStatusResponse:
    return codebase_service.get_index_status(repository_id)


@router.get("/{repository_id}/index/jobs", response_model=IndexJobListResponse)
def list_indexing_jobs(repository_id: str) -> IndexJobListResponse:
    return codebase_service.list_indexing_jobs(repository_id)


@router.post("/{repository_id}/index/jobs/{job_id}/pause", response_model=IndexJobControlResponse)
def pause_indexing_job(repository_id: str, job_id: str) -> IndexJobControlResponse:
    result = codebase_service.pause_indexing_job(repository_id, job_id)
    return IndexJobControlResponse(**result)


@router.post("/{repository_id}/index/jobs/{job_id}/resume", response_model=IndexJobControlResponse)
def resume_indexing_job(repository_id: str, job_id: str) -> IndexJobControlResponse:
    result = codebase_service.resume_indexing_job(repository_id, job_id)
    return IndexJobControlResponse(**result)


@router.post("/{repository_id}/index/jobs/{job_id}/cancel", response_model=IndexJobControlResponse)
def cancel_indexing_job(repository_id: str, job_id: str) -> IndexJobControlResponse:
    result = codebase_service.cancel_indexing_job(repository_id, job_id)
    return IndexJobControlResponse(**result)


@router.get("/{repository_id}/index/jobs/{job_id}/warnings", response_model=IndexWarningsResponse)
def get_index_warnings(repository_id: str, job_id: str) -> IndexWarningsResponse:
    return codebase_service.get_index_warnings(repository_id, job_id)


@router.get("/{repository_id}/index/jobs/{job_id}/skipped-files", response_model=SkippedFilesResponse)
def get_skipped_files(repository_id: str, job_id: str) -> SkippedFilesResponse:
    return codebase_service.get_skipped_files(repository_id, job_id)


@router.get("/{repository_id}/index/jobs/{job_id}/failed-files", response_model=FailedFilesResponse)
def get_failed_files(repository_id: str, job_id: str) -> FailedFilesResponse:
    return codebase_service.get_failed_files(repository_id, job_id)


@router.get("/{repository_id}/staleness", response_model=StalenessResponse)
def get_staleness(repository_id: str) -> StalenessResponse:
    return codebase_service.get_staleness(repository_id)
