from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.auth import require_api_auth
from app.schemas.imports import (
    GitHubImportRequest,
    ImportCancelResponse,
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
    ImportSessionCreateResponse,
)
from app.services.codebase_service import codebase_service


router = APIRouter(prefix="/import-sessions", tags=["import-sessions"], dependencies=[Depends(require_api_auth)])


@router.post("/upload-zip", response_model=ImportSessionCreateResponse)
async def create_zip_import_session(file: UploadFile = File(...), name: str | None = Form(default=None)) -> ImportSessionCreateResponse:
    return await codebase_service.create_zip_import_session(file, name)


@router.post("/upload-folder", response_model=ImportSessionCreateResponse)
async def create_folder_import_session(
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    name: str | None = Form(default=None),
) -> ImportSessionCreateResponse:
    return await codebase_service.create_folder_import_session(files, relative_paths, name)


@router.post("/github", response_model=ImportSessionCreateResponse)
def create_github_import_session(request: GitHubImportRequest) -> ImportSessionCreateResponse:
    return codebase_service.create_github_import_session(request.url, request.name, request.branch)


@router.get("/{import_session_id}/preview", response_model=ImportPreviewResponse)
def get_import_preview(import_session_id: str) -> ImportPreviewResponse:
    return codebase_service.get_import_preview(import_session_id)


@router.post("/{import_session_id}/confirm", response_model=ImportConfirmResponse)
def confirm_import_session(import_session_id: str, request: ImportConfirmRequest) -> ImportConfirmResponse:
    return codebase_service.confirm_import_session(
        import_session_id,
        request.name,
        request.start_indexing,
        request.duplicate_action,
        run_in_background=True,
    )


@router.delete("/{import_session_id}", response_model=ImportCancelResponse)
def cancel_import_session(import_session_id: str) -> ImportCancelResponse:
    return codebase_service.cancel_import_session(import_session_id)
