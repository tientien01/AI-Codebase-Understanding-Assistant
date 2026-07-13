from __future__ import annotations

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    indexing: dict[str, str | int | bool]
    providers: dict[str, str | bool]
    security: dict[str, bool]


class IgnorePatternsResponse(BaseModel):
    default_patterns: list[str]
    user_patterns: list[str] = Field(default_factory=list)
    effective_patterns: list[str]
