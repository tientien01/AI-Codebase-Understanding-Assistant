from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import require_api_auth
from app.schemas.exploration import EndpointListResponse, OverviewResponse, ReadingPathResponse, SymbolListResponse
from app.services.codebase_service import codebase_service


router = APIRouter(prefix="/repositories", tags=["repositories"], dependencies=[Depends(require_api_auth)])


@router.get("/{repository_id}/overview", response_model=OverviewResponse)
def get_overview(repository_id: str) -> OverviewResponse:
    return codebase_service.get_overview(repository_id)


@router.get("/{repository_id}/reading-path", response_model=ReadingPathResponse)
def get_reading_path(repository_id: str) -> ReadingPathResponse:
    return codebase_service.get_reading_path(repository_id)


@router.get("/{repository_id}/symbols", response_model=SymbolListResponse)
def list_symbols(repository_id: str, q: str | None = None, symbol_type: str | None = None) -> SymbolListResponse:
    return codebase_service.list_symbols(repository_id, q, symbol_type)


@router.get("/{repository_id}/api/endpoints", response_model=EndpointListResponse)
def list_endpoints(repository_id: str) -> EndpointListResponse:
    return codebase_service.list_endpoints(repository_id)
