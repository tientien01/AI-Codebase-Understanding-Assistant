from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import text

from app.api.dependencies import get_access_service
from app.core.config import Settings, settings
from app.core.errors import DomainError
from app.main import app
from app.services.security import AccessConfiguration, AccessService, InMemoryAccessStore, ProductionAccessStore
from app.services.security.credentials import hash_password, hash_secret, verify_password


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 7, 14, 8, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def _service() -> tuple[AccessService, InMemoryAccessStore, Clock]:
    store = InMemoryAccessStore()
    clock = Clock()
    service = AccessService(
        store,
        AccessConfiguration(
            bootstrap_credential="bootstrap-secret",
            allowed_origins=frozenset({"https://operator.example"}),
            session_absolute_seconds=3600,
            session_idle_seconds=300,
            api_token_max_seconds=7200,
        ),
        clock=clock,
    )
    return service, store, clock


def _bootstrap(service: AccessService):
    return service.bootstrap("bootstrap-secret", "correct horse battery staple", "Operator")


def test_versioned_password_and_secret_hashes_do_not_store_raw_values() -> None:
    password = "correct horse battery staple"
    verifier = hash_password(password, salt=b"a" * 16)
    assert verifier.startswith("scrypt$v1$32768$8$1$")
    assert password not in verifier
    assert verify_password(password, verifier)
    assert not verify_password("incorrect password", verifier)

    secret_verifier = hash_secret("presented-secret", salt=b"b" * 16)
    assert secret_verifier.startswith("sha256$v1$")
    assert "presented-secret" not in secret_verifier


def test_bootstrap_is_one_time_and_audits_without_credentials() -> None:
    service, store, _ = _service()
    issued = _bootstrap(service)

    assert issued.session_token.startswith("session_")
    assert store.principal is not None
    assert "correct horse battery staple" not in store.principal.password_hash
    with pytest.raises(DomainError) as caught:
        _bootstrap(service)
    assert (caught.value.code, caught.value.status_code) == ("BOOTSTRAP_DISABLED", 409)

    serialized_audits = repr(store.audits)
    assert "bootstrap-secret" not in serialized_audits
    assert "correct horse battery staple" not in serialized_audits
    assert [event.outcome for event in store.audits] == ["succeeded", "denied"]


def test_browser_session_requires_origin_and_csrf_for_mutations_and_expires_idle() -> None:
    service, _, clock = _service()
    issued = _bootstrap(service)

    principal = service.authenticate(
        authorization=None,
        session_cookie=issued.session_token,
        method="GET",
        origin=None,
        csrf_token=None,
    )
    assert principal.principal_id == issued.principal.principal_id

    with pytest.raises(DomainError) as missing_csrf:
        service.authenticate(
            authorization=None,
            session_cookie=issued.session_token,
            method="POST",
            origin="https://operator.example",
            csrf_token=None,
        )
    assert (missing_csrf.value.code, missing_csrf.value.status_code) == ("CSRF_VALIDATION_FAILED", 403)

    service.authenticate(
        authorization=None,
        session_cookie=issued.session_token,
        method="POST",
        origin="https://operator.example",
        csrf_token=issued.csrf_token,
    )
    clock.now += timedelta(seconds=301)
    with pytest.raises(DomainError) as expired:
        service.authenticate(
            authorization=None,
            session_cookie=issued.session_token,
            method="GET",
            origin=None,
            csrf_token=None,
        )
    assert expired.value.code == "AUTHENTICATION_REQUIRED"
    assert expired.value.headers == {"WWW-Authenticate": "Bearer"}


def test_named_api_token_is_shown_once_and_enforces_expiry_and_revocation() -> None:
    service, store, _ = _service()
    principal = _bootstrap(service).principal
    issued = service.create_api_token(principal, "automation", 600)

    record = store.api_tokens[issued.token_id]
    assert issued.token not in record.token_hash
    authenticated = service.authenticate(
        authorization=f"Bearer {issued.token}",
        session_cookie=None,
        method="POST",
        origin=None,
        csrf_token=None,
    )
    assert authenticated.credential_kind == "api_token"

    service.revoke_api_token(principal, issued.token_id)
    with pytest.raises(DomainError) as revoked:
        service.authenticate(
            authorization=f"Bearer {issued.token}",
            session_cookie=None,
            method="GET",
            origin=None,
            csrf_token=None,
        )
    assert revoked.value.code == "AUTHENTICATION_REQUIRED"


def test_repository_owner_denial_is_non_disclosing_and_audited() -> None:
    service, store, _ = _service()
    principal = _bootstrap(service).principal
    store.set_repository_owner("repo_owned", principal.principal_id)
    store.set_repository_owner("repo_foreign", "principal_other")

    service.authorize_repository(principal, "repo_owned")
    for repository_id in ("repo_foreign", "repo_missing"):
        with pytest.raises(DomainError) as denied:
            service.authorize_repository(principal, repository_id)
        assert (denied.value.code, denied.value.message, denied.value.status_code) == (
            "RESOURCE_NOT_FOUND",
            "Resource not found.",
            404,
        )
    denials = [event for event in store.audits if event.event_type == "authorization.repository"]
    assert len(denials) == 2
    assert all(event.details == {"reason_code": "not_found_or_not_owned"} for event in denials)


def test_recovery_revokes_all_sessions_and_tokens() -> None:
    service, store, _ = _service()
    first = _bootstrap(service)
    second = service.login("correct horse battery staple")
    service.create_api_token(first.principal, "first", 600)
    service.create_api_token(second.principal, "second", 600)

    assert service.recover_operator_password("new correct horse battery staple") == (2, 2)
    assert all(record.revoked_at is not None for record in store.sessions.values())
    assert all(record.revoked_at is not None for record in store.api_tokens.values())
    with pytest.raises(DomainError):
        service.login("correct horse battery staple")
    assert service.login("new correct horse battery staple").principal.principal_id == first.principal.principal_id


def test_production_settings_require_explicit_access_boundary() -> None:
    base = {
        "_env_file": None,
        "app_env": "production",
        "database_url": "postgresql+psycopg://localhost/app",
        "redis_url": "redis://localhost:6379/0",
        "artifact_root": "storage/artifacts",
        "index_lease_seconds": 30,
        "index_heartbeat_seconds": 10,
        "index_max_attempts": 3,
    }
    with pytest.raises(ValidationError, match="explicit operator access"):
        Settings(**base)
    with pytest.raises(ValidationError, match="forbids the shared"):
        Settings(
            **base,
            api_auth_token="legacy-shared",
            operator_bootstrap_credential="bootstrap",
            session_absolute_seconds=3600,
            session_idle_seconds=300,
            api_token_max_seconds=7200,
            audit_retention_seconds=86400,
        )


def test_http_cookie_csrf_bearer_and_repository_denial_matrix(monkeypatch) -> None:
    service, store, _ = _service()
    app.dependency_overrides[get_access_service] = lambda: service
    app.state.access_service = service
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "session_absolute_seconds", 3600)
    try:
        with TestClient(app, base_url="https://operator.example") as client:
            bootstrap = client.post(
                "/api/v1/auth/bootstrap",
                headers={"X-Bootstrap-Credential": "bootstrap-secret"},
                json={"display_name": "Operator", "password": "correct horse battery staple"},
            )
            assert bootstrap.status_code == 201
            assert "HttpOnly" in bootstrap.headers["set-cookie"]
            assert "SameSite=strict" in bootstrap.headers["set-cookie"]
            assert "Secure" in bootstrap.headers["set-cookie"]
            csrf_token = bootstrap.json()["csrf_token"]

            missing_csrf = client.post(
                "/api/v1/auth/tokens",
                headers={"Origin": "https://operator.example"},
                json={"name": "automation", "expires_in_seconds": 600},
            )
            assert missing_csrf.status_code == 403

            token_response = client.post(
                "/api/v1/auth/tokens",
                headers={"Origin": "https://operator.example", "X-CSRF-Token": csrf_token},
                json={"name": "automation", "expires_in_seconds": 600},
            )
            assert token_response.status_code == 201
            raw_token = token_response.json()["token"]
            session = client.get(
                "/api/v1/auth/session",
                headers={"Authorization": f"Bearer {raw_token}"},
            )
            assert session.status_code == 200
            assert session.json()["credential_kind"] == "api_token"

            store.set_repository_owner("repo_foreign", "principal_other")
            denial = client.delete(
                "/api/v1/repositories/repo_foreign",
                headers={"Authorization": f"Bearer {raw_token}"},
            )
            assert denial.status_code == 404
            assert denial.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


def test_postgresql_access_records_store_only_verifiers_and_append_audit(production_database) -> None:
    _, engine, _ = production_database
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO operator_principals (id, display_name) VALUES ('principal_existing', 'Existing')")
        )
    service = AccessService(
        ProductionAccessStore(engine),
        AccessConfiguration(
            bootstrap_credential="bootstrap-secret",
            allowed_origins=frozenset({"https://operator.example"}),
        ),
    )
    issued = _bootstrap(service)
    assert issued.principal.principal_id == "principal_existing"
    token = service.create_api_token(issued.principal, "integration", 600)

    with engine.connect() as connection:
        password_hash = connection.scalar(text("SELECT password_hash FROM operator_principals"))
        token_hash = connection.scalar(text("SELECT token_hash FROM operator_api_tokens"))
        audit_count = connection.scalar(text("SELECT count(*) FROM audit_events"))
    assert "correct horse battery staple" not in password_hash
    assert token.token not in token_hash
    assert audit_count == 2
