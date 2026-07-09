from __future__ import annotations

try:
    from fastapi import Header
except ImportError:  # pragma: no cover - keeps core unit tests framework-light.
    def Header(default=None):
        return default

from app.core.config import settings
from app.core.errors import DomainError


def require_api_auth(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> None:
    expected = settings.api_auth_token.strip()
    if not expected:
        return
    provided = _bearer_token(authorization) or (x_api_key or "").strip()
    if provided != expected:
        raise DomainError("UNAUTHORIZED", "A valid API token is required.", 401)


def _bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()
