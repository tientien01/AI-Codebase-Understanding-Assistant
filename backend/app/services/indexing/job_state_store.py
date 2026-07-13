"""Transactional PostgreSQL commands for job/version/artifact state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from sqlalchemy import Engine, insert, select, update
from sqlalchemy.exc import IntegrityError

from app.db.production_base import ProductionBase
import app.db.production_models  # noqa: F401


JOB_TRANSITIONS = {
    "queued": {"running", "cancelled"},
    "running": {"succeeded", "succeeded_with_warnings", "failed", "cancelled"},
}
VERSION_TRANSITIONS = {
    "building": {"validating", "failed", "cancelled"},
    "validating": {"failed", "cancelled"},
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class StateTransitionError(RuntimeError):
    pass


@dataclass(frozen=True)
class JobSubmission:
    job_id: str
    repository_id: str
    source_snapshot_id: str
    version_id: str
    version_number: int
    principal_id: str
    idempotency_record_id: str
    idempotency_key: str
    request_sha256: str
    repository_generation: int = 0
    build_kind: str = "full"


class JobStateStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.t = ProductionBase.metadata.tables

    def submit(self, command: JobSubmission) -> None:
        if not SHA256.fullmatch(command.request_sha256):
            raise ValueError("request_sha256 must be lowercase SHA-256")
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(self.t["idempotency_records"]).values(
                    id=command.idempotency_record_id, principal_id=command.principal_id,
                    operation="submit_index", idempotency_key=command.idempotency_key,
                    normalized_request_hash=command.request_sha256, state="completed",
                    resource_type="index_job", resource_id=command.job_id,
                    expires_at=datetime(2100, 1, 1, tzinfo=UTC),
                ))
                connection.execute(insert(self.t["index_versions"]).values(
                    id=command.version_id, repository_id=command.repository_id,
                    version_number=command.version_number, source_snapshot_id=command.source_snapshot_id,
                    build_kind=command.build_kind, lifecycle="building",
                    manifest_schema_version="index-manifest/v1", producer_version="job-state/v1",
                    configuration_sha256=command.request_sha256, critical_issue_count=0, coverage={},
                ))
                connection.execute(insert(self.t["index_jobs"]).values(
                    id=command.job_id, repository_id=command.repository_id,
                    source_snapshot_id=command.source_snapshot_id,
                    requested_build_kind=command.build_kind, effective_build_kind=command.build_kind,
                    target_index_version_id=command.version_id, state="queued",
                    idempotency_record_id=command.idempotency_record_id,
                    repository_generation=command.repository_generation,
                ))
        except IntegrityError as exc:
            raise StateTransitionError("Job submission conflicts with persisted ownership or active state") from exc

    def transition_job(self, job_id: str, expected: str, target: str) -> None:
        if target not in JOB_TRANSITIONS.get(expected, set()):
            raise StateTransitionError("Invalid job state transition")
        values = {"state": target}
        if target == "running":
            values["started_at"] = datetime.now(UTC)
        if target in {"succeeded", "succeeded_with_warnings", "failed", "cancelled"}:
            values["finished_at"] = datetime.now(UTC)
        with self.engine.begin() as connection:
            result = connection.execute(update(self.t["index_jobs"]).where(
                self.t["index_jobs"].c.id == job_id,
                self.t["index_jobs"].c.state == expected,
            ).values(**values))
            if result.rowcount != 1:
                raise StateTransitionError("Job state changed before the requested transition")

    def transition_version(self, version_id: str, expected: str, target: str) -> None:
        if target not in VERSION_TRANSITIONS.get(expected, set()):
            raise StateTransitionError("Invalid index-version state transition")
        values = {"lifecycle": target}
        if target in {"failed", "cancelled"}:
            values["finished_at"] = datetime.now(UTC)
        with self.engine.begin() as connection:
            result = connection.execute(update(self.t["index_versions"]).where(
                self.t["index_versions"].c.id == version_id,
                self.t["index_versions"].c.lifecycle == expected,
            ).values(**values))
            if result.rowcount != 1:
                raise StateTransitionError("Index-version state changed before the requested transition")

    def register_artifact(self, **values) -> None:
        sha256 = values.get("sha256", "")
        if not SHA256.fullmatch(sha256):
            raise ValueError("artifact sha256 must be lowercase SHA-256")
        if values.get("byte_size", -1) < 0 or values.get("record_count", -1) < 0:
            raise ValueError("artifact sizes and counts must be non-negative")
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(self.t["index_artifacts"]).values(**values))
        except IntegrityError as exc:
            raise StateTransitionError("Artifact conflicts with persisted identity or ownership") from exc

    def job_state(self, job_id: str) -> str | None:
        with self.engine.connect() as connection:
            return connection.scalar(select(self.t["index_jobs"].c.state).where(self.t["index_jobs"].c.id == job_id))

    def job_repository_id(self, job_id: str) -> str | None:
        with self.engine.connect() as connection:
            return connection.scalar(
                select(self.t["index_jobs"].c.repository_id).where(
                    self.t["index_jobs"].c.id == job_id
                )
            )
