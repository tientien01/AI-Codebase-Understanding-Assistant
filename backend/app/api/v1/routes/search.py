from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_search_use_cases
from app.core.auth import require_api_auth
from app.schemas.search import FileContentResponse, FileTreeNodeDTO, SearchResponse
from app.services.application.use_cases import SearchUseCases


router = APIRouter(prefix="/repositories", tags=["repositories"], dependencies=[Depends(require_api_auth)])


@router.get("/{repository_id}/search", response_model=SearchResponse)
def search(
    repository_id: str,
    q: str,
    service: SearchUseCases = Depends(get_search_use_cases),
) -> SearchResponse:
    return service.search(repository_id, q)


@router.get("/{repository_id}/files/tree", response_model=list[FileTreeNodeDTO])
def get_file_tree(
    repository_id: str,
    service: SearchUseCases = Depends(get_search_use_cases),
) -> list[FileTreeNodeDTO]:
    return service.get_file_tree(repository_id)


@router.get("/{repository_id}/files/content", response_model=FileContentResponse)
def get_file_content(
    repository_id: str,
    path: str,
    service: SearchUseCases = Depends(get_search_use_cases),
) -> FileContentResponse:
    return service.get_file_content(repository_id, path)
