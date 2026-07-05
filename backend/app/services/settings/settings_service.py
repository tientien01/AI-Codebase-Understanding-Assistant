from __future__ import annotations

from app.core.config import settings
from app.schemas.api import IgnorePatternsResponse, SettingsResponse
from app.services.scanning.file_rules import IGNORE_DIRS


class SettingsService:
    def get_settings(self) -> SettingsResponse:
        return SettingsResponse(
            indexing={
                "default_profile": "balanced",
                "max_file_size_mb": settings.max_file_size_mb,
                "max_upload_size_mb": settings.max_upload_size_mb,
            },
            providers={
                "llm_provider": settings.llm_provider,
                "llm_model": settings.llm_model,
                "llm_configured": bool(settings.llm_api_key) or settings.llm_provider == "fake",
                "embedding_provider": settings.embedding_provider,
                "embedding_model": settings.embedding_model,
                "embedding_configured": bool(settings.embedding_api_key) or settings.embedding_provider == "fake",
                "vector_store_provider": settings.vector_store_provider,
            },
            security={"secret_scanning_enabled": True},
        )

    def get_ignore_patterns(self) -> IgnorePatternsResponse:
        patterns = sorted([*IGNORE_DIRS, ".env", ".env.*", "secrets.*", "credentials.*", "*.pem", "*.key"])
        return IgnorePatternsResponse(default_patterns=patterns, user_patterns=[], effective_patterns=patterns)
