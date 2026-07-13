from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import require_api_auth
from app.schemas.search import FileContentResponse, FileTreeNodeDTO, SearchResponse
from app.services.codebase_service import codebase_service


router = APIRouter(prefix="/repositories", tags=["repositories"], dependencies=[Depends(require_api_auth)])


@router.get("/{repository_id}/search", response_model=SearchResponse)
def search(repository_id: str, q: str) -> SearchResponse:
    return codebase_service.search(repository_id, q)


@router.get("/{repository_id}/files/tree", response_model=list[FileTreeNodeDTO])
def get_file_tree(repository_id: str) -> list[FileTreeNodeDTO]:
    return codebase_service.get_file_tree(repository_id)


@router.get("/{repository_id}/files/content", response_model=FileContentResponse)
def get_file_content(repository_id: str, path: str) -> FileContentResponse:
    return codebase_service.get_file_content(repository_id, path)
