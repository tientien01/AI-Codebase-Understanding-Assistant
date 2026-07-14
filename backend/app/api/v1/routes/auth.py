"""Single-operator bootstrap, session, and API-token routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response, status

from app.api.dependencies import get_access_service
from app.core.auth import require_api_auth
from app.core.config import settings
from app.schemas.auth import (
    AccessOperationResponse,
    ApiTokenCreateRequest,
    ApiTokenIssuedResponse,
    BootstrapRequest,
    LoginRequest,
    SessionIssuedResponse,
    SessionResponse,
)
from app.services.security import AccessService, AuthenticatedPrincipal, IssuedSession


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/bootstrap", response_model=SessionIssuedResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_operator(
    payload: BootstrapRequest,
    response: Response,
    x_bootstrap_credential: str | None = Header(default=None),
    service: AccessService = Depends(get_access_service),
) -> SessionIssuedResponse:
    issued = service.bootstrap(x_bootstrap_credential or "", payload.password, payload.display_name)
    _set_session_cookie(response, issued)
    return _issued_session_response(issued)


@router.post("/login", response_model=SessionIssuedResponse)
def login_operator(
    payload: LoginRequest,
    response: Response,
    service: AccessService = Depends(get_access_service),
) -> SessionIssuedResponse:
    issued = service.login(payload.password)
    _set_session_cookie(response, issued)
    return _issued_session_response(issued)


@router.post("/logout", response_model=AccessOperationResponse)
def logout_operator(
    response: Response,
    principal: AuthenticatedPrincipal = Depends(require_api_auth),
    service: AccessService = Depends(get_access_service),
) -> AccessOperationResponse:
    service.logout(principal)
    response.delete_cookie("aica_session", path=settings.api_v1_prefix)
    return AccessOperationResponse(status="revoked")


@router.get("/session", response_model=SessionResponse)
def get_operator_session(
    principal: AuthenticatedPrincipal = Depends(require_api_auth),
) -> SessionResponse:
    return SessionResponse(
        principal_id=principal.principal_id,
        display_name=principal.display_name,
        credential_kind=principal.credential_kind,
    )


@router.post("/tokens", response_model=ApiTokenIssuedResponse, status_code=status.HTTP_201_CREATED)
def create_operator_token(
    payload: ApiTokenCreateRequest,
    principal: AuthenticatedPrincipal = Depends(require_api_auth),
    service: AccessService = Depends(get_access_service),
) -> ApiTokenIssuedResponse:
    issued = service.create_api_token(principal, payload.name, payload.expires_in_seconds)
    return ApiTokenIssuedResponse(
        token_id=issued.token_id,
        name=issued.name,
        token=issued.token,
        expires_at=issued.expires_at,
    )


@router.delete("/tokens/{token_id}", response_model=AccessOperationResponse)
def revoke_operator_token(
    token_id: str,
    principal: AuthenticatedPrincipal = Depends(require_api_auth),
    service: AccessService = Depends(get_access_service),
) -> AccessOperationResponse:
    service.revoke_api_token(principal, token_id)
    return AccessOperationResponse(status="revoked")


def _set_session_cookie(response: Response, issued: IssuedSession) -> None:
    response.set_cookie(
        "aica_session",
        issued.session_token,
        max_age=settings.session_absolute_seconds,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path=settings.api_v1_prefix,
    )


def _issued_session_response(issued: IssuedSession) -> SessionIssuedResponse:
    return SessionIssuedResponse(
        principal_id=issued.principal.principal_id,
        display_name=issued.principal.display_name,
        csrf_token=issued.csrf_token,
        expires_at=issued.expires_at,
    )
