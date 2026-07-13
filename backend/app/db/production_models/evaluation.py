"""Evaluation dataset, case, run, and result production tables."""

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import CHAR

from app.db.production_base import ProductionBase
from app.db.production_models.common import created_at, json_array, json_object, nonnegative, prefix_check, sha256_check

m = ProductionBase.metadata

evaluation_datasets = Table(
    "evaluation_datasets", m, Column("id", Text, primary_key=True), Column("name", Text, nullable=False), Column("version", Text, nullable=False),
    Column("schema_version", Text, nullable=False), Column("description", Text), Column("artifact_storage_key", Text, nullable=False),
    Column("artifact_sha256", CHAR(64), nullable=False), Column("status", Text, nullable=False), created_at(),
    UniqueConstraint("name", "version", name="uq_evaluation_datasets_name_version"), prefix_check("id", "dataset_", "id_prefix"),
    sha256_check("artifact_sha256", "artifact_sha256"), CheckConstraint("status IN ('draft','frozen','retired')", name="status"),
)

evaluation_cases = Table(
    "evaluation_cases", m, Column("id", Text, primary_key=True),
    Column("dataset_id", Text, ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False), Column("case_key", Text, nullable=False),
    Column("question", Text, nullable=False), json_object("ground_truth"), json_array("expected_evidence"), json_array("tags"), Column("ordinal", Integer, nullable=False), created_at(),
    UniqueConstraint("dataset_id", "case_key", name="uq_evaluation_cases_key"), UniqueConstraint("dataset_id", "ordinal", name="uq_evaluation_cases_ordinal"),
    prefix_check("id", "evalcase_", "id_prefix"), nonnegative("ordinal", "ordinal_nonnegative"),
)

evaluation_runs = Table(
    "evaluation_runs", m, Column("id", Text, primary_key=True),
    Column("dataset_id", Text, ForeignKey("evaluation_datasets.id", ondelete="RESTRICT"), nullable=False),
    Column("repository_id", Text, ForeignKey("repositories.id", ondelete="SET NULL")), Column("index_version_id", Text), Column("method", Text, nullable=False),
    Column("configuration_sha256", CHAR(64), nullable=False), Column("code_revision", Text, nullable=False), Column("ranking_version", Text), Column("workflow_version", Text),
    json_object("provider_identity"), json_object("environment_identity"), Column("state", Text, nullable=False),
    Column("started_at", DateTime(timezone=True)), Column("finished_at", DateTime(timezone=True)), created_at(),
    ForeignKeyConstraint(["repository_id", "index_version_id"], ["index_versions.repository_id", "index_versions.id"], ondelete="RESTRICT", name="fk_evaluation_runs_version"),
    prefix_check("id", "evalrun_", "id_prefix"), sha256_check("configuration_sha256", "configuration_sha256"),
    CheckConstraint("state IN ('queued','running','succeeded','failed','cancelled')", name="state"),
    CheckConstraint("(repository_id IS NULL) = (index_version_id IS NULL)", name="repository_version_pair"),
)
Index("ix_evaluation_runs_recent", evaluation_runs.c.dataset_id, evaluation_runs.c.created_at.desc(), evaluation_runs.c.id.desc())

evaluation_results = Table(
    "evaluation_results", m, Column("id", Text, primary_key=True), Column("run_id", Text, ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False),
    Column("case_id", Text, ForeignKey("evaluation_cases.id", ondelete="RESTRICT"), nullable=False),
    Column("trace_id", Text, ForeignKey("agent_traces.id", ondelete="SET NULL")), Column("answer", Text), Column("outcome", Text, nullable=False),
    json_array("retrieved_evidence"), json_array("citations"), json_object("automatic_metrics"), json_object("manual_scores"),
    Column("duration_ms", BigInteger), created_at(), UniqueConstraint("run_id", "case_id", name="uq_evaluation_results_case"),
    prefix_check("id", "evalresult_", "id_prefix"), CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="duration_ms_nonnegative"),
)
Index("ix_evaluation_results_run", evaluation_results.c.run_id, evaluation_results.c.case_id, evaluation_results.c.id)
