"""Repository, source snapshot, and import-session production tables."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR

from app.db.production_base import ProductionBase
from app.db.production_models.common import (
    created_at,
    json_array,
    json_object,
    json_type_check,
    nonnegative,
    paired,
    prefix_check,
    sha256_check,
    updated_at,
)

m = ProductionBase.metadata

repositories = Table(
    "repositories",
    m,
    Column("id", Text, primary_key=True),
    Column("owner_principal_id", Text, ForeignKey("operator_principals.id", ondelete="RESTRICT"), nullable=False),
    Column("display_name", Text, nullable=False),
    Column("lifecycle", Text, nullable=False, server_default=text("'active'")),
    Column("recovery_state", Text, nullable=False, server_default=text("'ready'")),
    Column("active_index_version_id", Text),
    Column("source_freshness", Text, nullable=False, server_default=text("'unverifiable'")),
    Column("operation_generation", BigInteger, nullable=False, server_default=text("0")),
    Column("deletion_requested_at", DateTime(timezone=True)),
    Column("deleted_at", DateTime(timezone=True)),
    created_at(),
    updated_at(),
    UniqueConstraint("id", "owner_principal_id", name="uq_repositories_owner"),
    prefix_check("id", "repo_", "id_prefix"),
    CheckConstraint("lifecycle IN ('active','deleting','deleted')", name="repositories_lifecycle"),
    CheckConstraint("recovery_state IN ('ready','blocked')", name="repository_recovery_state"),
    CheckConstraint(
        "source_freshness IN ('fresh','possibly_stale','stale','source_missing','unverifiable')",
        name="source_freshness",
    ),
    nonnegative("operation_generation", "operation_generation_nonnegative"),
    CheckConstraint(
        "lifecycle <> 'deleted' OR (active_index_version_id IS NULL AND deleted_at IS NOT NULL)",
        name="deleted_state",
    ),
)
Index("ix_repositories_owner_list", repositories.c.owner_principal_id, repositories.c.created_at.desc(), repositories.c.id.desc())
Index("ix_repositories_lifecycle", repositories.c.lifecycle, repositories.c.updated_at, repositories.c.id)

repository_sources = Table(
    "repository_sources",
    m,
    Column("id", Text, primary_key=True),
    Column("repository_id", Text, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
    Column("source_type", Text, nullable=False),
    Column("canonical_locator", Text),
    Column("credential_ref", Text),
    Column("default_ref", Text),
    Column("last_synchronized_revision", Text),
    Column("source_fingerprint", CHAR(64)),
    created_at(),
    updated_at(),
    UniqueConstraint("repository_id", "id", name="uq_repository_sources_owner"),
    prefix_check("id", "source_", "id_prefix"),
    CheckConstraint("source_type IN ('upload_zip','upload_folder','public_git')", name="repository_sources_type"),
    sha256_check("source_fingerprint", "source_fingerprint_sha256", nullable=True),
)
Index(
    "uq_repository_source_locator",
    repository_sources.c.repository_id,
    repository_sources.c.source_type,
    repository_sources.c.canonical_locator,
    unique=True,
    postgresql_where=repository_sources.c.canonical_locator.is_not(None),
)

source_snapshots = Table(
    "source_snapshots",
    m,
    Column("id", Text, primary_key=True),
    Column("repository_id", Text, nullable=False),
    Column("repository_source_id", Text, nullable=False),
    Column("revision", Text),
    Column("storage_key", Text, nullable=False),
    Column("snapshot_sha256", CHAR(64), nullable=False),
    Column("policy_version", Text, nullable=False),
    Column("inventory_schema_version", Text, nullable=False),
    Column("total_files", BigInteger, nullable=False),
    Column("total_bytes", BigInteger, nullable=False),
    created_at(),
    ForeignKeyConstraint(
        ["repository_id", "repository_source_id"],
        ["repository_sources.repository_id", "repository_sources.id"],
        ondelete="CASCADE",
        name="fk_source_snapshots_repository_source",
    ),
    UniqueConstraint("repository_id", "id", name="uq_source_snapshots_owner"),
    UniqueConstraint("repository_id", "repository_source_id", "snapshot_sha256", name="uq_source_snapshots_hash"),
    prefix_check("id", "snapshot_", "id_prefix"),
    sha256_check("snapshot_sha256", "snapshot_sha256"),
    nonnegative("total_files", "total_files_nonnegative"),
    nonnegative("total_bytes", "total_bytes_nonnegative"),
)

import_sessions = Table(
    "import_sessions",
    m,
    Column("id", Text, primary_key=True),
    Column("principal_id", Text, ForeignKey("operator_principals.id", ondelete="RESTRICT"), nullable=False),
    Column("source_type", Text, nullable=False),
    Column("state", Text, nullable=False, server_default=text("'created'")),
    Column("staging_key", Text),
    Column("preview_artifact_key", Text),
    Column("policy_version", Text, nullable=False),
    Column("source_fingerprint", CHAR(64)),
    Column("upload_bytes", BigInteger, nullable=False, server_default=text("0")),
    Column("indexable_bytes", BigInteger, nullable=False, server_default=text("0")),
    Column("total_files", BigInteger, nullable=False, server_default=text("0")),
    Column("indexable_files", BigInteger, nullable=False, server_default=text("0")),
    json_array("warnings"),
    json_array("duplicate_candidates"),
    json_object("limits"),
    Column("confirmed_repository_id", Text),
    Column("confirmed_snapshot_id", Text),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("confirmed_at", DateTime(timezone=True)),
    Column("cancelled_at", DateTime(timezone=True)),
    Column("failed_at", DateTime(timezone=True)),
    created_at(),
    updated_at(),
    ForeignKeyConstraint(
        ["confirmed_repository_id", "confirmed_snapshot_id"],
        ["source_snapshots.repository_id", "source_snapshots.id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
        name="fk_import_sessions_confirmed_snapshot",
    ),
    prefix_check("id", "import_", "id_prefix"),
    CheckConstraint("source_type IN ('upload_zip','upload_folder','public_git')", name="repository_sources_type"),
    CheckConstraint(
        "state IN ('created','acquiring','scanning','preview_ready','confirming','confirmed','cancelled','expired','failed')",
        name="import_sessions_state",
    ),
    sha256_check("source_fingerprint", "source_fingerprint_sha256", nullable=True),
    nonnegative("upload_bytes", "upload_bytes_nonnegative"),
    nonnegative("indexable_bytes", "indexable_bytes_nonnegative"),
    nonnegative("total_files", "total_files_nonnegative"),
    nonnegative("indexable_files", "indexable_files_nonnegative"),
    json_type_check("warnings", "array", "warnings_array"),
    json_type_check("duplicate_candidates", "array", "duplicate_candidates_array"),
    json_type_check("limits", "object", "limits_object"),
    paired("confirmed_repository_id", "confirmed_snapshot_id", "confirmed_snapshot_pair"),
)
Index(
    "ix_import_sessions_expiry",
    import_sessions.c.state,
    import_sessions.c.expires_at,
    import_sessions.c.id,
    postgresql_where=import_sessions.c.state.not_in(("confirmed", "cancelled", "expired", "failed")),
)
Index("ix_import_sessions_principal_history", import_sessions.c.principal_id, import_sessions.c.created_at.desc(), import_sessions.c.id.desc())
