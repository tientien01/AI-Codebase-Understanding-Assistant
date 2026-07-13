from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_settings_service
from app.core.auth import require_api_auth
from app.schemas.settings import IgnorePatternsResponse, SettingsResponse
from app.services.settings.settings_service import SettingsService


router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_api_auth)])


@router.get("", response_model=SettingsResponse)
def get_settings(service: SettingsService = Depends(get_settings_service)) -> SettingsResponse:
    return service.get_settings()


@router.get("/ignore-patterns", response_model=IgnorePatternsResponse)
def get_ignore_patterns(service: SettingsService = Depends(get_settings_service)) -> IgnorePatternsResponse:
    return service.get_ignore_patterns()
