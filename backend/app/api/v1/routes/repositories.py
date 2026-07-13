from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies import get_repository_use_cases
from app.core.auth import require_api_auth
from app.schemas.repositories import (
    RepositoryBulkDeleteRequest,
    RepositoryBulkDeleteResponse,
    RepositoryCreateResponse,
    RepositoryDTO,
    RepositoryDeleteResponse,
)
from app.services.application.use_cases import RepositoryUseCases


router = APIRouter(prefix="/repositories", tags=["repositories"], dependencies=[Depends(require_api_auth)])


@router.get("", response_model=list[RepositoryDTO])
def list_repositories(service: RepositoryUseCases = Depends(get_repository_use_cases)) -> list[RepositoryDTO]:
    return service.list_repositories()


@router.post("/bulk-delete", response_model=RepositoryBulkDeleteResponse)
def delete_repositories(
    request: RepositoryBulkDeleteRequest,
    service: RepositoryUseCases = Depends(get_repository_use_cases),
) -> RepositoryBulkDeleteResponse:
    return service.delete_repositories(request.repository_ids, request.delete_all)


@router.delete("/{repository_id}", response_model=RepositoryDeleteResponse)
def delete_repository(
    repository_id: str,
    service: RepositoryUseCases = Depends(get_repository_use_cases),
) -> RepositoryDeleteResponse:
    return service.delete_repository(repository_id)


@router.post("/upload", response_model=RepositoryCreateResponse)
async def upload_repository(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    service: RepositoryUseCases = Depends(get_repository_use_cases),
) -> RepositoryCreateResponse:
    return await service.upload_zip(file, name)


@router.post("/upload-folder", response_model=RepositoryCreateResponse)
async def upload_folder_repository(
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    name: str | None = Form(default=None),
    service: RepositoryUseCases = Depends(get_repository_use_cases),
) -> RepositoryCreateResponse:
    return await service.upload_folder(files, relative_paths, name)
