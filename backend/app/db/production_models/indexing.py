"""Durable indexing, attempt, artifact, and readiness production tables."""

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, ForeignKeyConstraint, Index, Integer, SmallInteger, Table, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CHAR

from app.db.production_base import ProductionBase
from app.db.production_models.common import created_at, json_array, json_object, json_type_check, nonnegative, paired, positive, prefix_check, range_check, sha256_check, updated_at

m = ProductionBase.metadata

index_versions = Table(
    "index_versions", m,
    Column("id", Text, primary_key=True), Column("repository_id", Text, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
    Column("version_number", BigInteger, nullable=False), Column("source_snapshot_id", Text, nullable=False),
    Column("base_index_version_id", Text), Column("build_kind", Text, nullable=False),
    Column("lifecycle", Text, nullable=False, server_default=text("'building'")),
    Column("manifest_schema_version", Text, nullable=False), Column("producer_version", Text, nullable=False),
    Column("configuration_sha256", CHAR(64), nullable=False), Column("manifest_storage_key", Text), Column("manifest_sha256", CHAR(64)),
    Column("validation_status", Text), Column("critical_issue_count", Integer, nullable=False, server_default=text("0")), json_object("coverage"),
    Column("started_at", DateTime(timezone=True), nullable=False, server_default=text("now()")), Column("finished_at", DateTime(timezone=True)),
    Column("activated_at", DateTime(timezone=True)), Column("superseded_at", DateTime(timezone=True)), Column("expired_at", DateTime(timezone=True)), created_at(),
    ForeignKeyConstraint(["repository_id", "source_snapshot_id"], ["source_snapshots.repository_id", "source_snapshots.id"], ondelete="RESTRICT", name="fk_index_versions_source_snapshot"),
    ForeignKeyConstraint(["repository_id", "base_index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="RESTRICT", name="fk_index_versions_base", use_alter=True),
    UniqueConstraint("repository_id", "id", name="uq_index_versions_owner"),
    UniqueConstraint("repository_id", "version_number", name="uq_index_versions_number"),
    prefix_check("id", "idx_", "id_prefix"), positive("version_number", "version_number_positive"),
    CheckConstraint("build_kind IN ('full','incremental')", name="build_kind"),
    CheckConstraint("lifecycle IN ('building','validating','ready','ready_with_warnings','active','superseded','expired','failed','cancelled')", name="index_versions_lifecycle"),
    sha256_check("configuration_sha256", "configuration_sha256"), sha256_check("manifest_sha256", "manifest_sha256", nullable=True),
    paired("manifest_storage_key", "manifest_sha256", "manifest_pair"),
    CheckConstraint("validation_status IS NULL OR validation_status IN ('passed','passed_with_warnings','failed')", name="validation_status"),
    nonnegative("critical_issue_count", "critical_issue_count_nonnegative"),
    CheckConstraint("lifecycle NOT IN ('ready','ready_with_warnings','active') OR (manifest_storage_key IS NOT NULL AND finished_at IS NOT NULL)", name="ready_manifest"),
    CheckConstraint("lifecycle <> 'active' OR activated_at IS NOT NULL", name="active_timestamp"),
)
Index("uq_index_versions_one_active", index_versions.c.repository_id, unique=True, postgresql_where=index_versions.c.lifecycle == "active")
Index("ix_index_versions_repository_history", index_versions.c.repository_id, index_versions.c.version_number.desc(), index_versions.c.id)

index_jobs = Table(
    "index_jobs", m,
    Column("id", Text, primary_key=True), Column("repository_id", Text, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
    Column("source_snapshot_id", Text, nullable=False), Column("requested_build_kind", Text, nullable=False), Column("effective_build_kind", Text, nullable=False),
    Column("base_index_version_id", Text), Column("target_index_version_id", Text), Column("state", Text, nullable=False, server_default=text("'queued'")),
    Column("priority", SmallInteger, nullable=False, server_default=text("0")),
    Column("idempotency_record_id", Text, ForeignKey("idempotency_records.id", ondelete="RESTRICT"), nullable=False, unique=True),
    Column("current_attempt_id", Text), Column("lease_generation", BigInteger, nullable=False, server_default=text("0")),
    Column("repository_generation", BigInteger, nullable=False), Column("stage_code", Text, nullable=False, server_default=text("'queued'")),
    Column("progress_completed", BigInteger), Column("progress_total", BigInteger), Column("progress_unit", Text),
    Column("cancellation_requested_at", DateTime(timezone=True)), Column("warning_count", Integer, nullable=False, server_default=text("0")),
    Column("error_code", Text), Column("error_message_safe", Text), Column("queued_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("started_at", DateTime(timezone=True)), Column("finished_at", DateTime(timezone=True)), created_at(), updated_at(),
    ForeignKeyConstraint(["repository_id", "source_snapshot_id"], ["source_snapshots.repository_id", "source_snapshots.id"], ondelete="RESTRICT", name="fk_index_jobs_source_snapshot"),
    ForeignKeyConstraint(["repository_id", "base_index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="RESTRICT", name="fk_index_jobs_base_version"),
    ForeignKeyConstraint(["repository_id", "target_index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="RESTRICT", name="fk_index_jobs_target_version"),
    UniqueConstraint("repository_id", "id", name="uq_index_jobs_owner"), prefix_check("id", "job_", "id_prefix"),
    CheckConstraint("requested_build_kind IN ('full','incremental')", name="requested_build_kind"),
    CheckConstraint("effective_build_kind IN ('full','incremental')", name="effective_build_kind"),
    CheckConstraint("state IN ('queued','running','succeeded','succeeded_with_warnings','failed','cancelled')", name="index_jobs_state"),
    nonnegative("lease_generation", "lease_generation_nonnegative"), nonnegative("repository_generation", "repository_generation_nonnegative"),
    nonnegative("warning_count", "warning_count_nonnegative"), paired("progress_completed", "progress_total", "progress_pair"),
    CheckConstraint("progress_completed IS NULL OR (progress_completed >= 0 AND progress_total >= 0 AND progress_unit IS NOT NULL)", name="progress_values"),
    CheckConstraint("progress_completed IS NOT NULL OR progress_unit IS NULL", name="progress_unit_pair"),
    CheckConstraint("state <> 'running' OR started_at IS NOT NULL", name="running_started"),
    CheckConstraint("state NOT IN ('succeeded','succeeded_with_warnings','failed','cancelled') OR finished_at IS NOT NULL", name="terminal_finished"),
    CheckConstraint("state NOT IN ('succeeded','succeeded_with_warnings') OR target_index_version_id IS NOT NULL", name="succeeded_target"),
)
Index("uq_index_jobs_one_active", index_jobs.c.repository_id, unique=True, postgresql_where=index_jobs.c.state.in_(("queued", "running")))
Index("ix_index_jobs_recovery", index_jobs.c.state, index_jobs.c.updated_at, index_jobs.c.id, postgresql_where=index_jobs.c.state.in_(("queued", "running")))
Index("ix_index_jobs_repository_history", index_jobs.c.repository_id, index_jobs.c.created_at.desc(), index_jobs.c.id.desc())

index_artifacts = Table(
    "index_artifacts", m,
    Column("id", Text, primary_key=True), Column("repository_id", Text, nullable=False), Column("index_version_id", Text, nullable=False),
    Column("artifact_type", Text, nullable=False), Column("storage_key", Text, nullable=False, unique=True), Column("schema_version", Text, nullable=False),
    Column("sha256", CHAR(64), nullable=False), Column("byte_size", BigInteger, nullable=False), Column("record_count", BigInteger, nullable=False),
    Column("producer_stage", Text, nullable=False), Column("producer_name", Text, nullable=False), Column("producer_version", Text, nullable=False),
    Column("required", Boolean, nullable=False, server_default=text("false")), Column("retention_class", Text, nullable=False),
    Column("finalized_at", DateTime(timezone=True), nullable=False), created_at(),
    ForeignKeyConstraint(["repository_id", "index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="CASCADE", name="fk_index_artifacts_version"),
    UniqueConstraint("repository_id", "index_version_id", "id", name="uq_index_artifacts_owner"),
    UniqueConstraint("repository_id", "index_version_id", "artifact_type", "storage_key", name="uq_index_artifacts_manifest_entry"),
    prefix_check("id", "artifact_", "id_prefix"), sha256_check("sha256", "sha256"),
    nonnegative("byte_size", "byte_size_nonnegative"), nonnegative("record_count", "record_count_nonnegative"),
    CheckConstraint("retention_class IN ('active_required','retained_previous_evidence','evaluation_audit','failed_build_diagnostic','temporary_debug')", name="retention_class"),
)
Index("ix_index_artifacts_manifest", index_artifacts.c.repository_id, index_artifacts.c.index_version_id, index_artifacts.c.artifact_type, index_artifacts.c.id)

job_attempts = Table(
    "job_attempts", m,
    Column("id", Text, primary_key=True), Column("job_id", Text, nullable=False), Column("repository_id", Text, nullable=False),
    Column("lease_generation", BigInteger, nullable=False), Column("worker_id", Text, nullable=False), Column("state", Text, nullable=False, server_default=text("'claimed'")),
    Column("lease_expires_at", DateTime(timezone=True), nullable=False), Column("heartbeat_at", DateTime(timezone=True), nullable=False),
    Column("checkpoint_stage", Text), Column("checkpoint_artifact_id", Text, ForeignKey("index_artifacts.id", ondelete="SET NULL")),
    Column("error_code", Text), Column("error_message_safe", Text), Column("claimed_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("finished_at", DateTime(timezone=True)),
    ForeignKeyConstraint(["repository_id", "job_id"], ["index_jobs.repository_id", "index_jobs.id"], ondelete="CASCADE", name="fk_job_attempts_job"),
    UniqueConstraint("job_id", "id", name="uq_job_attempts_job"), UniqueConstraint("repository_id", "job_id", "id", name="uq_job_attempts_owner"),
    UniqueConstraint("job_id", "lease_generation", name="uq_job_attempts_generation"), prefix_check("id", "attempt_", "id_prefix"),
    positive("lease_generation", "lease_generation_positive"),
    CheckConstraint("state IN ('claimed','running','succeeded','failed','cancelled','lease_lost')", name="job_attempts_state"),
)
Index("ix_job_attempts_stale_lease", job_attempts.c.state, job_attempts.c.lease_expires_at, job_attempts.c.id, postgresql_where=job_attempts.c.state.in_(("claimed", "running")))

repositories = m.tables["repositories"]
repositories.append_constraint(ForeignKeyConstraint([repositories.c.id, repositories.c.active_index_version_id], [index_versions.c.repository_id, index_versions.c.id], ondelete="RESTRICT", deferrable=True, initially="DEFERRED", name="fk_repositories_active_version", use_alter=True))
index_jobs.append_constraint(ForeignKeyConstraint([index_jobs.c.repository_id, index_jobs.c.id, index_jobs.c.current_attempt_id], [job_attempts.c.repository_id, job_attempts.c.job_id, job_attempts.c.id], ondelete="RESTRICT", deferrable=True, initially="DEFERRED", name="fk_index_jobs_current_attempt", use_alter=True))

validation_issues = Table(
    "validation_issues", m,
    Column("id", Text, primary_key=True), Column("repository_id", Text, nullable=False), Column("index_version_id", Text, nullable=False),
    Column("code", Text, nullable=False), Column("severity", Text, nullable=False), Column("entity_type", Text), Column("entity_key", Text), Column("file_key", Text),
    Column("start_line", Integer), Column("end_line", Integer), Column("message_safe", Text, nullable=False), json_object("details"), created_at(),
    ForeignKeyConstraint(["repository_id", "index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="CASCADE", name="fk_validation_issues_version"),
    prefix_check("id", "issue_", "id_prefix"), CheckConstraint("severity IN ('info','warning','error','critical')", name="severity"),
    range_check("start_line", "end_line", "source_range", nullable=True),
)
Index("ix_validation_issues_version_severity", validation_issues.c.repository_id, validation_issues.c.index_version_id, validation_issues.c.severity, validation_issues.c.id)

capability_readiness = Table(
    "capability_readiness", m,
    Column("id", Text, primary_key=True), Column("repository_id", Text, nullable=False), Column("index_version_id", Text, nullable=False),
    Column("capability", Text, nullable=False), Column("state", Text, nullable=False), json_array("reason_codes"), json_array("required_artifact_types"),
    Column("validation_issue_id", Text, ForeignKey("validation_issues.id", ondelete="SET NULL")), json_object("coverage"), Column("remediation", Text), created_at(), updated_at(),
    ForeignKeyConstraint(["repository_id", "index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="CASCADE", name="fk_capability_readiness_version"),
    UniqueConstraint("repository_id", "index_version_id", "capability", name="uq_capability_readiness_capability"),
    prefix_check("id", "capability_", "id_prefix"), CheckConstraint("state IN ('ready','limited','unavailable','failed','stale')", name="capability_state"),
    json_type_check("reason_codes", "array", "reason_codes_array"), json_type_check("required_artifact_types", "array", "required_artifact_types_array"),
)
