"""Single-operator authentication, authorization, and audit policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hmac
import secrets
from typing import Callable

from app.core.errors import DomainError
from app.services.security.access_store import (
    AccessStore,
    ApiTokenRecord,
    AuditRecord,
    PrincipalRecord,
    SessionRecord,
)
from app.services.security.credentials import (
    credential_record_id,
    hash_password,
    issue_secret,
    verify_password,
    verify_presented_secret,
)


SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class AccessConfiguration:
    bootstrap_credential: str
    allowed_origins: frozenset[str]
    session_absolute_seconds: int = 43_200
    session_idle_seconds: int = 1_800
    api_token_max_seconds: int = 7_776_000


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    principal_id: str
    display_name: str
    credential_kind: str
    credential_id: str


@dataclass(frozen=True)
class IssuedSession:
    principal: AuthenticatedPrincipal
    session_token: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True)
class IssuedApiToken:
    token_id: str
    name: str
    token: str
    expires_at: datetime


class AccessService:
    """Own authentication state transitions and safe audit semantics."""

    def __init__(
        self,
        store: AccessStore,
        configuration: AccessConfiguration,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.configuration = configuration
        self.clock = clock or (lambda: datetime.now(UTC))
        if min(
            configuration.session_absolute_seconds,
            configuration.session_idle_seconds,
            configuration.api_token_max_seconds,
        ) <= 0:
            raise ValueError("Access lifetimes must be positive")
        if configuration.session_idle_seconds > configuration.session_absolute_seconds:
            raise ValueError("Session idle lifetime cannot exceed absolute lifetime")

    def bootstrap(
        self,
        bootstrap_credential: str,
        password: str,
        display_name: str,
        *,
        request_id: str | None = None,
    ) -> IssuedSession:
        if not self.configuration.bootstrap_credential or not hmac.compare_digest(
            bootstrap_credential,
            self.configuration.bootstrap_credential,
        ):
            self.store.append_audit(self._audit("operator.bootstrap", "denied", request_id=request_id, reason="credential_invalid"))
            raise self._authentication_error()
        clean_name = display_name.strip()
        if not 1 <= len(clean_name) <= 120:
            raise DomainError("VALIDATION_ERROR", "Display name must be between 1 and 120 characters.", 422)
        now = self.clock()
        pending_principal = self.store.pending_bootstrap_principal()
        principal = PrincipalRecord(
            id=pending_principal.id if pending_principal else "principal_" + secrets.token_hex(16),
            display_name=clean_name,
            status="active",
            password_hash=hash_password(password),
        )
        issued, session_record = self._new_session(principal, now)
        audit = self._audit(
            "operator.bootstrap",
            "succeeded",
            principal_id=principal.id,
            resource_type="operator_principal",
            resource_id=principal.id,
            request_id=request_id,
        )
        if not self.store.bootstrap(principal, session_record, audit):
            self.store.append_audit(self._audit("operator.bootstrap", "denied", request_id=request_id, reason="already_initialized"))
            raise DomainError("BOOTSTRAP_DISABLED", "Operator bootstrap is no longer available.", 409)
        return issued

    def login(self, password: str, *, request_id: str | None = None) -> IssuedSession:
        principal = self.store.get_operator()
        if principal is None or principal.status != "active" or not verify_password(password, principal.password_hash):
            self.store.append_audit(
                self._audit(
                    "operator.login",
                    "denied",
                    principal_id=principal.id if principal else None,
                    request_id=request_id,
                    reason="credential_invalid",
                )
            )
            raise self._authentication_error()
        now = self.clock()
        issued, record = self._new_session(principal, now)
        self.store.create_session(
            record,
            self._audit(
                "operator.login",
                "succeeded",
                principal_id=principal.id,
                resource_type="operator_session",
                resource_id=record.id,
                request_id=request_id,
            ),
        )
        return issued

    def authenticate(
        self,
        *,
        authorization: str | None,
        session_cookie: str | None,
        method: str,
        origin: str | None,
        csrf_token: str | None,
        request_id: str | None = None,
    ) -> AuthenticatedPrincipal:
        bearer = _bearer_token(authorization)
        if bearer:
            return self._authenticate_api_token(bearer, request_id=request_id)
        if session_cookie:
            return self._authenticate_session(
                session_cookie,
                method=method,
                origin=origin,
                csrf_token=csrf_token,
                request_id=request_id,
            )
        raise self._authentication_error()

    def logout(self, principal: AuthenticatedPrincipal, *, request_id: str | None = None) -> None:
        if principal.credential_kind != "session":
            raise DomainError("VALIDATION_ERROR", "Logout requires a browser session.", 400)
        now = self.clock()
        self.store.revoke_session(
            principal.credential_id,
            now,
            self._audit(
                "operator.logout",
                "succeeded",
                principal_id=principal.principal_id,
                resource_type="operator_session",
                resource_id=principal.credential_id,
                request_id=request_id,
            ),
        )

    def create_api_token(
        self,
        principal: AuthenticatedPrincipal,
        name: str,
        expires_in_seconds: int,
        *,
        request_id: str | None = None,
    ) -> IssuedApiToken:
        clean_name = name.strip()
        if not 1 <= len(clean_name) <= 120:
            raise DomainError("VALIDATION_ERROR", "Token name must be between 1 and 120 characters.", 422)
        if not 1 <= expires_in_seconds <= self.configuration.api_token_max_seconds:
            raise DomainError("VALIDATION_ERROR", "Token lifetime exceeds the configured maximum.", 422)
        now = self.clock()
        token_id = "token_" + secrets.token_hex(16)
        presented, verifier = issue_secret(token_id)
        expires_at = now + timedelta(seconds=expires_in_seconds)
        record = ApiTokenRecord(token_id, principal.principal_id, clean_name, verifier, expires_at)
        self.store.create_api_token(
            record,
            self._audit(
                "operator.token.create",
                "succeeded",
                principal_id=principal.principal_id,
                resource_type="operator_api_token",
                resource_id=token_id,
                request_id=request_id,
            ),
        )
        return IssuedApiToken(token_id, clean_name, presented, expires_at)

    def revoke_api_token(
        self,
        principal: AuthenticatedPrincipal,
        token_id: str,
        *,
        request_id: str | None = None,
    ) -> None:
        record = self.store.get_api_token(token_id)
        if record is None or record.principal_id != principal.principal_id:
            raise DomainError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        revoked = self.store.revoke_api_token(
            token_id,
            self.clock(),
            self._audit(
                "operator.token.revoke",
                "succeeded",
                principal_id=principal.principal_id,
                resource_type="operator_api_token",
                resource_id=token_id,
                request_id=request_id,
            ),
        )
        if not revoked:
            raise DomainError("RESOURCE_NOT_FOUND", "Resource not found.", 404)

    def authorize_repository(
        self,
        principal: AuthenticatedPrincipal,
        repository_id: str,
        *,
        request_id: str | None = None,
    ) -> None:
        owner = self.store.repository_owner(repository_id)
        if owner == principal.principal_id:
            return
        self.store.append_audit(
            self._audit(
                "authorization.repository",
                "denied",
                principal_id=principal.principal_id,
                repository_id=repository_id if owner is not None else None,
                resource_type="repository",
                resource_id=repository_id,
                request_id=request_id,
                reason="not_found_or_not_owned",
            )
        )
        raise DomainError("RESOURCE_NOT_FOUND", "Resource not found.", 404)

    def revoke_all_access(self, *, request_id: str | None = None) -> tuple[int, int]:
        principal = self.store.get_operator()
        now = self.clock()
        return self.store.revoke_all(
            now,
            self._audit(
                "operator.recovery.revoke_all",
                "succeeded",
                principal_id=principal.id if principal else None,
                resource_type="operator_principal" if principal else None,
                resource_id=principal.id if principal else None,
                request_id=request_id,
            ),
        )

    def recover_operator_password(self, new_password: str, *, request_id: str | None = None) -> tuple[int, int]:
        """Trusted-host recovery rotates the verifier and revokes all credentials."""

        principal = self.store.get_operator()
        now = self.clock()
        return self.store.rotate_password_and_revoke_all(
            hash_password(new_password),
            now,
            self._audit(
                "operator.recovery.rotate_password",
                "succeeded",
                principal_id=principal.id if principal else None,
                resource_type="operator_principal" if principal else None,
                resource_id=principal.id if principal else None,
                request_id=request_id,
            ),
        )

    def _authenticate_session(
        self,
        presented: str,
        *,
        method: str,
        origin: str | None,
        csrf_token: str | None,
        request_id: str | None,
    ) -> AuthenticatedPrincipal:
        session_id = credential_record_id(presented, "session_")
        record = self.store.get_session(session_id) if session_id else None
        now = self.clock()
        principal = self.store.get_operator()
        invalid = (
            record is None
            or principal is None
            or record.principal_id != principal.id
            or principal.status != "active"
            or record.revoked_at is not None
            or record.expires_at <= now
            or record.last_seen_at + timedelta(seconds=self.configuration.session_idle_seconds) <= now
            or not verify_presented_secret(presented, record.id, record.token_hash)
        )
        if invalid:
            self.store.append_audit(self._audit("operator.session.authenticate", "denied", request_id=request_id, reason="invalid_or_expired"))
            raise self._authentication_error()
        if method.upper() not in SAFE_METHODS:
            csrf_valid = bool(csrf_token) and verify_presented_secret(csrf_token or "", record.id, record.csrf_secret_hash)
            if origin not in self.configuration.allowed_origins or not csrf_valid:
                self.store.append_audit(
                    self._audit(
                        "operator.session.csrf",
                        "denied",
                        principal_id=principal.id,
                        request_id=request_id,
                        reason="origin_or_token_invalid",
                    )
                )
                raise DomainError("CSRF_VALIDATION_FAILED", "CSRF validation failed.", 403)
        self.store.touch_session(record.id, now)
        return AuthenticatedPrincipal(principal.id, principal.display_name, "session", record.id)

    def _authenticate_api_token(self, presented: str, *, request_id: str | None) -> AuthenticatedPrincipal:
        token_id = credential_record_id(presented, "token_")
        record = self.store.get_api_token(token_id) if token_id else None
        now = self.clock()
        principal = self.store.get_operator()
        invalid = (
            record is None
            or principal is None
            or record.principal_id != principal.id
            or principal.status != "active"
            or record.revoked_at is not None
            or record.expires_at <= now
            or not verify_presented_secret(presented, record.id, record.token_hash)
        )
        if invalid:
            self.store.append_audit(self._audit("operator.token.authenticate", "denied", request_id=request_id, reason="invalid_or_expired"))
            raise self._authentication_error()
        self.store.touch_api_token(record.id, now)
        return AuthenticatedPrincipal(principal.id, principal.display_name, "api_token", record.id)

    def _new_session(self, principal: PrincipalRecord, now: datetime) -> tuple[IssuedSession, SessionRecord]:
        session_id = "session_" + secrets.token_hex(16)
        session_token, token_hash = issue_secret(session_id)
        csrf_token, csrf_hash = issue_secret(session_id)
        expires_at = now + timedelta(seconds=self.configuration.session_absolute_seconds)
        record = SessionRecord(session_id, principal.id, token_hash, csrf_hash, expires_at, now)
        authenticated = AuthenticatedPrincipal(principal.id, principal.display_name, "session", session_id)
        return IssuedSession(authenticated, session_token, csrf_token, expires_at), record

    def _audit(
        self,
        event_type: str,
        outcome: str,
        *,
        principal_id: str | None = None,
        repository_id: str | None = None,
        request_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        reason: str | None = None,
    ) -> AuditRecord:
        details: dict[str, object] = {}
        if reason:
            details["reason_code"] = reason
        return AuditRecord(
            id="audit_" + secrets.token_hex(16),
            principal_id=principal_id,
            repository_id=repository_id,
            request_id=request_id,
            event_type=event_type,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )

    @staticmethod
    def _authentication_error() -> DomainError:
        return DomainError(
            "AUTHENTICATION_REQUIRED",
            "Authentication is required.",
            401,
            headers={"WWW-Authenticate": "Bearer"},
        )


def _bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    scheme, separator, token = value.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()
