"""Persistence ports for the operator access boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from threading import RLock
from typing import Protocol

from sqlalchemy import Engine, insert, select, update

from app.db.production_base import ProductionBase
import app.db.production_models  # noqa: F401 - register production tables
from app.db.production_session import create_production_session_factory


@dataclass(frozen=True)
class PrincipalRecord:
    id: str
    display_name: str
    status: str
    password_hash: str


@dataclass(frozen=True)
class SessionRecord:
    id: str
    principal_id: str
    token_hash: str
    csrf_secret_hash: str
    expires_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class ApiTokenRecord:
    id: str
    principal_id: str
    name: str
    token_hash: str
    expires_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class AuditRecord:
    id: str
    principal_id: str | None
    repository_id: str | None
    request_id: str | None
    event_type: str
    outcome: str
    resource_type: str | None
    resource_id: str | None
    details: dict[str, object]


class AccessStore(Protocol):
    def pending_bootstrap_principal(self) -> PrincipalRecord | None: ...
    def bootstrap(self, principal: PrincipalRecord, session: SessionRecord, audit: AuditRecord) -> bool: ...
    def get_operator(self) -> PrincipalRecord | None: ...
    def create_session(self, session: SessionRecord, audit: AuditRecord) -> None: ...
    def get_session(self, session_id: str) -> SessionRecord | None: ...
    def touch_session(self, session_id: str, last_seen_at: datetime) -> None: ...
    def revoke_session(self, session_id: str, revoked_at: datetime, audit: AuditRecord) -> None: ...
    def create_api_token(self, token: ApiTokenRecord, audit: AuditRecord) -> None: ...
    def get_api_token(self, token_id: str) -> ApiTokenRecord | None: ...
    def touch_api_token(self, token_id: str, last_used_at: datetime) -> None: ...
    def revoke_api_token(self, token_id: str, revoked_at: datetime, audit: AuditRecord) -> bool: ...
    def revoke_all(self, revoked_at: datetime, audit: AuditRecord) -> tuple[int, int]: ...
    def rotate_password_and_revoke_all(self, password_hash: str, revoked_at: datetime, audit: AuditRecord) -> tuple[int, int]: ...
    def repository_owner(self, repository_id: str) -> str | None: ...
    def append_audit(self, audit: AuditRecord) -> None: ...


class InMemoryAccessStore:
    """Thread-safe local/test adapter with the same fail-closed semantics."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.principal: PrincipalRecord | None = None
        self.sessions: dict[str, SessionRecord] = {}
        self.api_tokens: dict[str, ApiTokenRecord] = {}
        self.repository_owners: dict[str, str] = {}
        self.audits: list[AuditRecord] = []

    def bootstrap(self, principal: PrincipalRecord, session: SessionRecord, audit: AuditRecord) -> bool:
        with self._lock:
            if self.principal is not None and self.principal.password_hash:
                return False
            self.principal = principal
            self.sessions[session.id] = session
            self.audits.append(audit)
            return True

    def pending_bootstrap_principal(self) -> PrincipalRecord | None:
        with self._lock:
            if self.principal is not None and not self.principal.password_hash:
                return self.principal
            return None

    def get_operator(self) -> PrincipalRecord | None:
        with self._lock:
            return self.principal

    def create_session(self, session: SessionRecord, audit: AuditRecord) -> None:
        with self._lock:
            self.sessions[session.id] = session
            self.audits.append(audit)

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            return self.sessions.get(session_id)

    def touch_session(self, session_id: str, last_seen_at: datetime) -> None:
        with self._lock:
            record = self.sessions.get(session_id)
            if record is not None:
                self.sessions[session_id] = replace(record, last_seen_at=last_seen_at)

    def revoke_session(self, session_id: str, revoked_at: datetime, audit: AuditRecord) -> None:
        with self._lock:
            record = self.sessions.get(session_id)
            if record is not None and record.revoked_at is None:
                self.sessions[session_id] = replace(record, revoked_at=revoked_at)
            self.audits.append(audit)

    def create_api_token(self, token: ApiTokenRecord, audit: AuditRecord) -> None:
        with self._lock:
            self.api_tokens[token.id] = token
            self.audits.append(audit)

    def get_api_token(self, token_id: str) -> ApiTokenRecord | None:
        with self._lock:
            return self.api_tokens.get(token_id)

    def touch_api_token(self, token_id: str, last_used_at: datetime) -> None:
        with self._lock:
            record = self.api_tokens.get(token_id)
            if record is not None:
                self.api_tokens[token_id] = replace(record, last_used_at=last_used_at)

    def revoke_api_token(self, token_id: str, revoked_at: datetime, audit: AuditRecord) -> bool:
        with self._lock:
            record = self.api_tokens.get(token_id)
            if record is None or record.revoked_at is not None:
                return False
            self.api_tokens[token_id] = replace(record, revoked_at=revoked_at)
            self.audits.append(audit)
            return True

    def revoke_all(self, revoked_at: datetime, audit: AuditRecord) -> tuple[int, int]:
        with self._lock:
            session_count = sum(record.revoked_at is None for record in self.sessions.values())
            token_count = sum(record.revoked_at is None for record in self.api_tokens.values())
            self.sessions = {
                key: replace(value, revoked_at=revoked_at) if value.revoked_at is None else value
                for key, value in self.sessions.items()
            }
            self.api_tokens = {
                key: replace(value, revoked_at=revoked_at) if value.revoked_at is None else value
                for key, value in self.api_tokens.items()
            }
            self.audits.append(audit)
            return session_count, token_count

    def rotate_password_and_revoke_all(self, password_hash: str, revoked_at: datetime, audit: AuditRecord) -> tuple[int, int]:
        with self._lock:
            if self.principal is None:
                raise RuntimeError("Operator is not initialized")
            self.principal = replace(self.principal, password_hash=password_hash, status="active")
        return self.revoke_all(revoked_at, audit)

    def repository_owner(self, repository_id: str) -> str | None:
        with self._lock:
            return self.repository_owners.get(repository_id)

    def set_repository_owner(self, repository_id: str, principal_id: str) -> None:
        with self._lock:
            self.repository_owners[repository_id] = principal_id

    def append_audit(self, audit: AuditRecord) -> None:
        with self._lock:
            self.audits.append(audit)


class ProductionAccessStore:
    """PostgreSQL adapter over the accepted access and ownership tables."""

    def __init__(self, engine: Engine) -> None:
        self.Session = create_production_session_factory(engine)
        self.t = ProductionBase.metadata.tables

    def pending_bootstrap_principal(self) -> PrincipalRecord | None:
        with self.Session() as session:
            rows = session.execute(
                select(self.t["operator_principals"]).order_by(self.t["operator_principals"].c.id).limit(2)
            ).mappings().all()
        if len(rows) != 1 or rows[0]["password_hash"]:
            return None
        row = rows[0]
        return PrincipalRecord(row["id"], row["display_name"], row["status"], "")

    def bootstrap(self, principal: PrincipalRecord, session_record: SessionRecord, audit: AuditRecord) -> bool:
        with self.Session.begin() as session:
            principals = session.execute(
                select(self.t["operator_principals"]).with_for_update().order_by(self.t["operator_principals"].c.id).limit(2)
            ).mappings().all()
            if len(principals) > 1 or (principals and principals[0]["password_hash"]):
                return False
            if principals:
                if principals[0]["id"] != principal.id:
                    return False
                session.execute(
                    update(self.t["operator_principals"])
                    .where(self.t["operator_principals"].c.id == principal.id)
                    .values(display_name=principal.display_name, status="active", password_hash=principal.password_hash)
                )
            else:
                session.execute(insert(self.t["operator_principals"]).values(**principal.__dict__))
            session.execute(insert(self.t["operator_sessions"]).values(**session_record.__dict__))
            session.execute(insert(self.t["audit_events"]).values(**audit.__dict__))
            return True

    def get_operator(self) -> PrincipalRecord | None:
        with self.Session() as session:
            rows = session.execute(
                select(self.t["operator_principals"]).order_by(self.t["operator_principals"].c.id).limit(2)
            ).mappings().all()
        if len(rows) != 1 or not rows[0]["password_hash"]:
            return None
        row = rows[0]
        return PrincipalRecord(row["id"], row["display_name"], row["status"], row["password_hash"])

    def create_session(self, record: SessionRecord, audit: AuditRecord) -> None:
        with self.Session.begin() as session:
            session.execute(insert(self.t["operator_sessions"]).values(**record.__dict__))
            session.execute(insert(self.t["audit_events"]).values(**audit.__dict__))

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self.Session() as session:
            row = session.execute(
                select(self.t["operator_sessions"]).where(self.t["operator_sessions"].c.id == session_id)
            ).mappings().first()
        return _session_record(row) if row else None

    def touch_session(self, session_id: str, last_seen_at: datetime) -> None:
        with self.Session.begin() as session:
            session.execute(update(self.t["operator_sessions"]).where(self.t["operator_sessions"].c.id == session_id).values(last_seen_at=last_seen_at))

    def revoke_session(self, session_id: str, revoked_at: datetime, audit: AuditRecord) -> None:
        with self.Session.begin() as session:
            session.execute(update(self.t["operator_sessions"]).where(self.t["operator_sessions"].c.id == session_id).values(revoked_at=revoked_at))
            session.execute(insert(self.t["audit_events"]).values(**audit.__dict__))

    def create_api_token(self, record: ApiTokenRecord, audit: AuditRecord) -> None:
        with self.Session.begin() as session:
            session.execute(insert(self.t["operator_api_tokens"]).values(**record.__dict__))
            session.execute(insert(self.t["audit_events"]).values(**audit.__dict__))

    def get_api_token(self, token_id: str) -> ApiTokenRecord | None:
        with self.Session() as session:
            row = session.execute(
                select(self.t["operator_api_tokens"]).where(self.t["operator_api_tokens"].c.id == token_id)
            ).mappings().first()
        return _api_token_record(row) if row else None

    def touch_api_token(self, token_id: str, last_used_at: datetime) -> None:
        with self.Session.begin() as session:
            session.execute(update(self.t["operator_api_tokens"]).where(self.t["operator_api_tokens"].c.id == token_id).values(last_used_at=last_used_at))

    def revoke_api_token(self, token_id: str, revoked_at: datetime, audit: AuditRecord) -> bool:
        with self.Session.begin() as session:
            result = session.execute(
                update(self.t["operator_api_tokens"])
                .where(self.t["operator_api_tokens"].c.id == token_id, self.t["operator_api_tokens"].c.revoked_at.is_(None))
                .values(revoked_at=revoked_at)
            )
            if result.rowcount != 1:
                return False
            session.execute(insert(self.t["audit_events"]).values(**audit.__dict__))
            return True

    def revoke_all(self, revoked_at: datetime, audit: AuditRecord) -> tuple[int, int]:
        with self.Session.begin() as session:
            sessions = session.execute(update(self.t["operator_sessions"]).where(self.t["operator_sessions"].c.revoked_at.is_(None)).values(revoked_at=revoked_at)).rowcount
            tokens = session.execute(update(self.t["operator_api_tokens"]).where(self.t["operator_api_tokens"].c.revoked_at.is_(None)).values(revoked_at=revoked_at)).rowcount
            session.execute(insert(self.t["audit_events"]).values(**audit.__dict__))
            return sessions, tokens

    def rotate_password_and_revoke_all(self, password_hash: str, revoked_at: datetime, audit: AuditRecord) -> tuple[int, int]:
        with self.Session.begin() as session:
            principals = session.execute(select(self.t["operator_principals"].c.id).with_for_update().limit(2)).scalars().all()
            if len(principals) != 1:
                raise RuntimeError("Operator identity is not uniquely initialized")
            session.execute(
                update(self.t["operator_principals"])
                .where(self.t["operator_principals"].c.id == principals[0])
                .values(password_hash=password_hash, status="active")
            )
            sessions = session.execute(update(self.t["operator_sessions"]).where(self.t["operator_sessions"].c.revoked_at.is_(None)).values(revoked_at=revoked_at)).rowcount
            tokens = session.execute(update(self.t["operator_api_tokens"]).where(self.t["operator_api_tokens"].c.revoked_at.is_(None)).values(revoked_at=revoked_at)).rowcount
            session.execute(insert(self.t["audit_events"]).values(**audit.__dict__))
            return sessions, tokens

    def repository_owner(self, repository_id: str) -> str | None:
        with self.Session() as session:
            return session.scalar(select(self.t["repositories"].c.owner_principal_id).where(self.t["repositories"].c.id == repository_id))

    def append_audit(self, audit: AuditRecord) -> None:
        with self.Session.begin() as session:
            session.execute(insert(self.t["audit_events"]).values(**audit.__dict__))


def _session_record(row) -> SessionRecord:
    return SessionRecord(
        id=row["id"], principal_id=row["principal_id"], token_hash=row["token_hash"],
        csrf_secret_hash=row["csrf_secret_hash"], expires_at=row["expires_at"],
        last_seen_at=row["last_seen_at"], revoked_at=row["revoked_at"],
    )


def _api_token_record(row) -> ApiTokenRecord:
    return ApiTokenRecord(
        id=row["id"], principal_id=row["principal_id"], name=row["name"],
        token_hash=row["token_hash"], expires_at=row["expires_at"],
        last_used_at=row["last_used_at"], revoked_at=row["revoked_at"],
    )
