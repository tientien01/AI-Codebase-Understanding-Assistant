from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import require_api_auth
from app.schemas.settings import IgnorePatternsResponse, SettingsResponse
from app.services.codebase_service import codebase_service


router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_api_auth)])


@router.get("", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    return codebase_service.get_settings()


@router.get("/ignore-patterns", response_model=IgnorePatternsResponse)
def get_ignore_patterns() -> IgnorePatternsResponse:
    return codebase_service.get_ignore_patterns()
