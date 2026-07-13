"""Operator access, idempotency, deletion, and audit production tables."""

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, SmallInteger, Table, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CHAR

from app.db.production_base import ProductionBase
from app.db.production_models.common import created_at, json_object, nonnegative, paired, prefix_check, sha256_check, updated_at

m = ProductionBase.metadata

operator_principals = Table(
    "operator_principals", m,
    Column("id", Text, primary_key=True), Column("display_name", Text, nullable=False),
    Column("status", Text, nullable=False, server_default=text("'active'")), created_at(), updated_at(),
    prefix_check("id", "principal_", "id_prefix"),
    CheckConstraint("status IN ('active','disabled')", name="status"),
)

operator_sessions = Table(
    "operator_sessions", m,
    Column("id", Text, primary_key=True),
    Column("principal_id", Text, ForeignKey("operator_principals.id", ondelete="CASCADE"), nullable=False),
    Column("token_hash", Text, nullable=False, unique=True), Column("csrf_secret_hash", Text, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False), Column("last_seen_at", DateTime(timezone=True)),
    Column("revoked_at", DateTime(timezone=True)), created_at(), prefix_check("id", "session_", "id_prefix"),
)

operator_api_tokens = Table(
    "operator_api_tokens", m,
    Column("id", Text, primary_key=True),
    Column("principal_id", Text, ForeignKey("operator_principals.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False), Column("token_hash", Text, nullable=False, unique=True),
    Column("last_used_at", DateTime(timezone=True)), Column("expires_at", DateTime(timezone=True)),
    Column("revoked_at", DateTime(timezone=True)), created_at(), prefix_check("id", "token_", "id_prefix"),
)

idempotency_records = Table(
    "idempotency_records", m,
    Column("id", Text, primary_key=True),
    Column("principal_id", Text, ForeignKey("operator_principals.id", ondelete="RESTRICT"), nullable=False),
    Column("operation", Text, nullable=False), Column("idempotency_key", Text, nullable=False),
    Column("normalized_request_hash", CHAR(64), nullable=False), Column("state", Text, nullable=False),
    Column("http_status", SmallInteger), Column("resource_type", Text), Column("resource_id", Text),
    Column("response_ref", Text), Column("expires_at", DateTime(timezone=True), nullable=False), created_at(), updated_at(),
    UniqueConstraint("principal_id", "operation", "idempotency_key", name="uq_idempotency_scope"),
    prefix_check("id", "idem_", "id_prefix"), sha256_check("normalized_request_hash", "normalized_request_hash_sha256"),
    CheckConstraint("state IN ('in_progress','completed','failed')", name="state"),
    CheckConstraint("http_status IS NULL OR http_status BETWEEN 100 AND 599", name="http_status"),
    paired("resource_type", "resource_id", "resource_pair"),
)

repository_deletion_operations = Table(
    "repository_deletion_operations", m,
    Column("id", Text, primary_key=True),
    Column("repository_id", Text, ForeignKey("repositories.id", ondelete="RESTRICT"), nullable=False),
    Column("idempotency_record_id", Text, ForeignKey("idempotency_records.id", ondelete="RESTRICT"), nullable=False, unique=True),
    Column("state", Text, nullable=False, server_default=text("'queued'")),
    Column("repository_generation", BigInteger, nullable=False), Column("attempt_count", Integer, nullable=False, server_default=text("0")),
    Column("last_error_code", Text), json_object("cleanup_summary"), Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)), created_at(), updated_at(), prefix_check("id", "delete_", "id_prefix"),
    CheckConstraint("state IN ('queued','running','partially_failed','succeeded','failed')", name="deletion_state"),
    nonnegative("repository_generation", "repository_generation_nonnegative"), nonnegative("attempt_count", "attempt_count_nonnegative"),
)
Index("uq_deletion_one_active", repository_deletion_operations.c.repository_id, unique=True,
      postgresql_where=repository_deletion_operations.c.state.in_(("queued", "running", "partially_failed")))

audit_events = Table(
    "audit_events", m,
    Column("id", Text, primary_key=True),
    Column("principal_id", Text, ForeignKey("operator_principals.id", ondelete="SET NULL")),
    Column("repository_id", Text, ForeignKey("repositories.id", ondelete="SET NULL")),
    Column("request_id", Text), Column("event_type", Text, nullable=False), Column("outcome", Text, nullable=False),
    Column("resource_type", Text), Column("resource_id", Text), json_object("details"), created_at(),
    prefix_check("id", "audit_", "id_prefix"),
)
Index("ix_audit_events_resource", audit_events.c.resource_type, audit_events.c.resource_id, audit_events.c.created_at.desc(), audit_events.c.id.desc())
