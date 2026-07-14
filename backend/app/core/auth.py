"""FastAPI authentication and repository-ownership dependency."""

from __future__ import annotations

from fastapi import Header, Request

from app.core.config import settings
from app.core.errors import DomainError
from app.services.security import AuthenticatedPrincipal


LOCAL_PRINCIPAL = AuthenticatedPrincipal(
    principal_id="principal_local_operator",
    display_name="Local operator",
    credential_kind="development_compatibility",
    credential_id="development_compatibility",
)


def require_api_auth(
    request: Request,
    authorization: str | None = Header(default=None),
) -> AuthenticatedPrincipal:
    """Resolve one principal and enforce path-level repository ownership."""

    x_request_id = request.headers.get("X-Request-ID")
    if settings.app_env != "production":
        principal = _local_compatibility_auth(
            authorization,
            request.headers.get("X-API-Key"),
        )
    else:
        service = request.app.state.access_service
        principal = service.authenticate(
            authorization=authorization,
            session_cookie=request.cookies.get("aica_session"),
            method=request.method,
            origin=request.headers.get("Origin"),
            csrf_token=request.headers.get("X-CSRF-Token"),
            request_id=_safe_request_id(x_request_id),
        )
        repository_id = request.path_params.get("repository_id")
        if repository_id:
            service.authorize_repository(
                principal,
                repository_id,
                request_id=_safe_request_id(x_request_id),
            )
    request.state.authenticated_principal = principal
    return principal


def _local_compatibility_auth(
    authorization: str | None,
    x_api_key: str | None,
) -> AuthenticatedPrincipal:
    expected = settings.api_auth_token.strip()
    if not expected:
        return LOCAL_PRINCIPAL
    provided = _bearer_token(authorization) or (x_api_key or "").strip()
    if provided != expected:
        raise DomainError(
            "AUTHENTICATION_REQUIRED",
            "Authentication is required.",
            401,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return LOCAL_PRINCIPAL


def _bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    scheme, separator, token = value.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _safe_request_id(value: str | None) -> str | None:
    if value and len(value) <= 128 and all(character.isalnum() or character in "-_.:" for character in value):
        return value
    return None
