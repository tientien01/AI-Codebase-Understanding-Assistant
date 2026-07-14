from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies import get_import_session_service
from app.core.auth import require_api_auth
from app.schemas.imports import (
    FolderImportBatchResponse,
    FolderImportStartRequest,
    GitHubImportRequest,
    ImportCancelResponse,
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
    ImportSessionCreateResponse,
    ImportSessionStatusResponse,
)
from app.services.ingestion.import_session_service import ImportSessionService


router = APIRouter(prefix="/import-sessions", tags=["import-sessions"], dependencies=[Depends(require_api_auth)])


@router.post("/upload-zip", response_model=ImportSessionCreateResponse)
async def create_zip_import_session(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    service: ImportSessionService = Depends(get_import_session_service),
) -> ImportSessionCreateResponse:
    return await service.create_zip_import_session(file, name)


@router.post("/upload-folder", response_model=ImportSessionCreateResponse)
async def create_folder_import_session(
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    name: str | None = Form(default=None),
    service: ImportSessionService = Depends(get_import_session_service),
) -> ImportSessionCreateResponse:
    return await service.create_folder_import_session(files, relative_paths, name)


@router.post("/upload-folder/start", response_model=ImportSessionCreateResponse)
def start_folder_import_session(
    request: FolderImportStartRequest,
    service: ImportSessionService = Depends(get_import_session_service),
) -> ImportSessionCreateResponse:
    return service.start_folder_import_session(request.name, request.total_files, request.total_bytes)


@router.post("/{import_session_id}/upload-folder-batch", response_model=FolderImportBatchResponse)
async def upload_folder_batch(
    import_session_id: str,
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    service: ImportSessionService = Depends(get_import_session_service),
) -> FolderImportBatchResponse:
    return await service.upload_folder_batch(import_session_id, files, relative_paths)


@router.post("/{import_session_id}/upload-folder-complete", response_model=ImportSessionCreateResponse)
def complete_folder_import_session(
    import_session_id: str,
    service: ImportSessionService = Depends(get_import_session_service),
) -> ImportSessionCreateResponse:
    return service.complete_folder_import_session(import_session_id)


@router.post("/github", response_model=ImportSessionCreateResponse)
def create_github_import_session(
    request: GitHubImportRequest,
    service: ImportSessionService = Depends(get_import_session_service),
) -> ImportSessionCreateResponse:
    return service.start_github_import_session(request.url, request.name, request.branch)


@router.get("/{import_session_id}/status", response_model=ImportSessionStatusResponse)
def get_import_session_status(
    import_session_id: str,
    service: ImportSessionService = Depends(get_import_session_service),
) -> ImportSessionStatusResponse:
    return service.get_import_session_status(import_session_id)


@router.get("/{import_session_id}/preview", response_model=ImportPreviewResponse)
def get_import_preview(
    import_session_id: str,
    service: ImportSessionService = Depends(get_import_session_service),
) -> ImportPreviewResponse:
    return service.get_import_preview(import_session_id)


@router.post("/{import_session_id}/confirm", response_model=ImportConfirmResponse)
def confirm_import_session(
    import_session_id: str,
    request: ImportConfirmRequest,
    service: ImportSessionService = Depends(get_import_session_service),
) -> ImportConfirmResponse:
    return service.confirm_import_session(
        import_session_id,
        request.name,
        request.start_indexing,
        request.duplicate_action,
        run_in_background=True,
    )


@router.delete("/{import_session_id}", response_model=ImportCancelResponse)
def cancel_import_session(
    import_session_id: str,
    service: ImportSessionService = Depends(get_import_session_service),
) -> ImportCancelResponse:
    return service.cancel_import_session(import_session_id)
