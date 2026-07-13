"""Transactional PostgreSQL commands for job/version/artifact state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
import re
from uuid import uuid4

from sqlalchemy import Engine, func, insert, select, update
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


class LeaseLostError(StateTransitionError):
    pass


class CancellationRequested(StateTransitionError):
    pass


class ClaimDisposition(str, Enum):
    CLAIMED = "claimed"
    DEFERRED = "deferred"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class JobLease:
    job_id: str
    repository_id: str
    attempt_id: str
    generation: int
    repository_generation: int
    lease_expires_at: datetime


@dataclass(frozen=True)
class ClaimResult:
    disposition: ClaimDisposition
    lease: JobLease | None = None
    retry_after_seconds: float | None = None


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

    def claim(
        self,
        job_id: str,
        worker_id: str,
        *,
        lease_seconds: int,
        max_attempts: int,
        now: datetime | None = None,
    ) -> ClaimResult:
        """Claim queued work or recover an expired attempt in one transaction."""
        now = now or datetime.now(UTC)
        expires_at = now + timedelta(seconds=lease_seconds)
        jobs, attempts, repositories = (
            self.t["index_jobs"],
            self.t["job_attempts"],
            self.t["repositories"],
        )
        with self.engine.begin() as connection:
            job = connection.execute(
                select(jobs).where(jobs.c.id == job_id).with_for_update()
            ).mappings().first()
            if job is None:
                raise StateTransitionError("Delivered index job does not exist")
            if job["state"] in {"succeeded", "succeeded_with_warnings", "failed", "cancelled"}:
                return ClaimResult(ClaimDisposition.TERMINAL)

            repository = connection.execute(
                select(repositories).where(
                    repositories.c.id == job["repository_id"]
                ).with_for_update()
            ).mappings().one()
            if job["cancellation_requested_at"] is not None:
                self._cancel_locked(connection, job, now)
                return ClaimResult(ClaimDisposition.TERMINAL)
            if (
                repository["lifecycle"] != "active"
                or repository["operation_generation"] != job["repository_generation"]
            ):
                self._fail_locked(
                    connection,
                    job,
                    now,
                    "REPOSITORY_FENCED",
                    "Repository no longer accepts this index job.",
                )
                return ClaimResult(ClaimDisposition.TERMINAL)

            if job["state"] == "running" and job["current_attempt_id"]:
                current = connection.execute(
                    select(attempts).where(
                        attempts.c.id == job["current_attempt_id"]
                    ).with_for_update()
                ).mappings().first()
                if current and current["lease_expires_at"] > now:
                    remaining = (current["lease_expires_at"] - now).total_seconds()
                    return ClaimResult(ClaimDisposition.DEFERRED, retry_after_seconds=remaining)
                if current and current["state"] in {"claimed", "running"}:
                    connection.execute(
                        update(attempts).where(attempts.c.id == current["id"]).values(
                            state="lease_lost",
                            error_code="LEASE_EXPIRED",
                            error_message_safe="Worker lease expired before completion.",
                            finished_at=now,
                        )
                    )

            attempt_count = connection.scalar(
                select(func.count()).select_from(attempts).where(
                    attempts.c.job_id == job_id
                )
            ) or 0
            if attempt_count >= max_attempts:
                self._fail_locked(
                    connection,
                    job,
                    now,
                    "ATTEMPT_BUDGET_EXHAUSTED",
                    "Index job exhausted its persistent attempt budget.",
                )
                return ClaimResult(ClaimDisposition.TERMINAL)

            generation = int(job["lease_generation"]) + 1
            attempt_id = f"attempt_{uuid4().hex}"
            connection.execute(
                insert(attempts).values(
                    id=attempt_id,
                    job_id=job_id,
                    repository_id=job["repository_id"],
                    lease_generation=generation,
                    worker_id=worker_id,
                    state="running",
                    lease_expires_at=expires_at,
                    heartbeat_at=now,
                )
            )
            connection.execute(
                update(jobs).where(jobs.c.id == job_id).values(
                    state="running",
                    current_attempt_id=attempt_id,
                    lease_generation=generation,
                    stage_code="running",
                    started_at=job["started_at"] or now,
                    finished_at=None,
                    error_code=None,
                    error_message_safe=None,
                )
            )
            lease = JobLease(
                job_id=job_id,
                repository_id=job["repository_id"],
                attempt_id=attempt_id,
                generation=generation,
                repository_generation=job["repository_generation"],
                lease_expires_at=expires_at,
            )
            return ClaimResult(ClaimDisposition.CLAIMED, lease=lease)

    def heartbeat(
        self,
        lease: JobLease,
        *,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> JobLease:
        now = now or datetime.now(UTC)
        with self.engine.begin() as connection:
            self._lock_owned_lease(connection, lease, now)
            expires_at = now + timedelta(seconds=lease_seconds)
            connection.execute(
                update(self.t["job_attempts"])
                .where(self.t["job_attempts"].c.id == lease.attempt_id)
                .values(heartbeat_at=now, lease_expires_at=expires_at)
            )
        return JobLease(**{**lease.__dict__, "lease_expires_at": expires_at})

    def complete(self, lease: JobLease, *, now: datetime | None = None) -> str:
        now = now or datetime.now(UTC)
        jobs, attempts = self.t["index_jobs"], self.t["job_attempts"]
        with self.engine.begin() as connection:
            job = self._lock_owned_lease(connection, lease, now)
            target = "succeeded_with_warnings" if job["warning_count"] else "succeeded"
            connection.execute(
                update(attempts).where(attempts.c.id == lease.attempt_id).values(
                    state="succeeded", finished_at=now
                )
            )
            connection.execute(
                update(jobs).where(jobs.c.id == lease.job_id).values(
                    state=target, stage_code="completed", finished_at=now
                )
            )
            return target

    def fail(
        self,
        lease: JobLease,
        *,
        retryable: bool,
        max_attempts: int,
        error_code: str,
        error_message_safe: str,
        now: datetime | None = None,
    ) -> bool:
        """Persist failure and return whether another delivery should be queued."""
        now = now or datetime.now(UTC)
        jobs, attempts = self.t["index_jobs"], self.t["job_attempts"]
        with self.engine.begin() as connection:
            job = self._lock_owned_lease(connection, lease, now)
            connection.execute(
                update(attempts).where(attempts.c.id == lease.attempt_id).values(
                    state="failed",
                    error_code=error_code,
                    error_message_safe=error_message_safe[:512],
                    finished_at=now,
                )
            )
            if retryable and lease.generation < max_attempts:
                connection.execute(
                    update(jobs).where(jobs.c.id == lease.job_id).values(
                        state="queued",
                        current_attempt_id=None,
                        stage_code="backoff",
                        error_code=error_code,
                        error_message_safe=error_message_safe[:512],
                        finished_at=None,
                    )
                )
                return True
            self._fail_locked(
                connection,
                job,
                now,
                error_code,
                error_message_safe,
                update_attempt=False,
            )
            return False

    def request_cancellation(
        self, job_id: str, *, now: datetime | None = None
    ) -> str:
        now = now or datetime.now(UTC)
        jobs = self.t["index_jobs"]
        with self.engine.begin() as connection:
            job = connection.execute(
                select(jobs).where(jobs.c.id == job_id).with_for_update()
            ).mappings().first()
            if job is None:
                raise StateTransitionError("Index job does not exist")
            if job["state"] == "queued":
                self._cancel_locked(connection, job, now)
                return "cancelled"
            if job["state"] == "running":
                connection.execute(
                    update(jobs).where(jobs.c.id == job_id).values(
                        cancellation_requested_at=job["cancellation_requested_at"] or now
                    )
                )
            return job["state"]

    def cancel(self, lease: JobLease, *, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        jobs, attempts, repositories = (
            self.t["index_jobs"], self.t["job_attempts"], self.t["repositories"]
        )
        with self.engine.begin() as connection:
            job = connection.execute(
                select(jobs).where(jobs.c.id == lease.job_id).with_for_update()
            ).mappings().one()
            attempt = connection.execute(
                select(attempts).where(
                    attempts.c.id == lease.attempt_id
                ).with_for_update()
            ).mappings().first()
            repository = connection.execute(
                select(repositories).where(
                    repositories.c.id == lease.repository_id
                ).with_for_update()
            ).mappings().one()
            if (
                job["state"] != "running"
                or job["current_attempt_id"] != lease.attempt_id
                or job["lease_generation"] != lease.generation
                or job["repository_generation"] != lease.repository_generation
                or job["cancellation_requested_at"] is None
                or attempt is None
                or attempt["state"] not in {"claimed", "running"}
                or attempt["lease_expires_at"] <= now
                or repository["lifecycle"] != "active"
                or repository["operation_generation"] != lease.repository_generation
            ):
                raise LeaseLostError("LEASE_LOST")
            connection.execute(
                update(attempts).where(attempts.c.id == lease.attempt_id).values(
                    state="cancelled", finished_at=now
                )
            )
            self._cancel_locked(connection, job, now, update_attempt=False)

    def job_details(self, job_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(self.t["index_jobs"]).where(self.t["index_jobs"].c.id == job_id)
            ).mappings().first()
            return dict(row) if row else None

    def attempt_details(self, attempt_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(self.t["job_attempts"]).where(
                    self.t["job_attempts"].c.id == attempt_id
                )
            ).mappings().first()
            return dict(row) if row else None

    def _lock_owned_lease(self, connection, lease: JobLease, now: datetime):
        jobs, attempts, repositories = (
            self.t["index_jobs"], self.t["job_attempts"], self.t["repositories"]
        )
        job = connection.execute(
            select(jobs).where(jobs.c.id == lease.job_id).with_for_update()
        ).mappings().one()
        attempt = connection.execute(
            select(attempts).where(attempts.c.id == lease.attempt_id).with_for_update()
        ).mappings().first()
        repository = connection.execute(
            select(repositories).where(
                repositories.c.id == lease.repository_id
            ).with_for_update()
        ).mappings().one()
        if job["cancellation_requested_at"] is not None:
            raise CancellationRequested("CANCELLATION_REQUESTED")
        valid = (
            job["state"] == "running"
            and job["current_attempt_id"] == lease.attempt_id
            and job["lease_generation"] == lease.generation
            and job["repository_generation"] == lease.repository_generation
            and attempt is not None
            and attempt["state"] in {"claimed", "running"}
            and attempt["lease_generation"] == lease.generation
            and attempt["lease_expires_at"] > now
            and repository["lifecycle"] == "active"
            and repository["operation_generation"] == lease.repository_generation
        )
        if not valid:
            raise LeaseLostError("LEASE_LOST")
        return job

    def _cancel_locked(
        self, connection, job, now: datetime, *, update_attempt: bool = True
    ) -> None:
        if update_attempt and job["current_attempt_id"]:
            connection.execute(
                update(self.t["job_attempts"])
                .where(
                    self.t["job_attempts"].c.id == job["current_attempt_id"],
                    self.t["job_attempts"].c.state.in_(("claimed", "running")),
                )
                .values(state="cancelled", finished_at=now)
            )
        connection.execute(
            update(self.t["index_jobs"]).where(
                self.t["index_jobs"].c.id == job["id"]
            ).values(
                state="cancelled",
                cancellation_requested_at=job["cancellation_requested_at"] or now,
                finished_at=now,
            )
        )
        self._finish_version(connection, job, "cancelled", now)

    def _fail_locked(
        self,
        connection,
        job,
        now: datetime,
        error_code: str,
        error_message_safe: str,
        *,
        update_attempt: bool = True,
    ) -> None:
        if update_attempt and job["current_attempt_id"]:
            connection.execute(
                update(self.t["job_attempts"])
                .where(
                    self.t["job_attempts"].c.id == job["current_attempt_id"],
                    self.t["job_attempts"].c.state.in_(("claimed", "running")),
                )
                .values(
                    state="failed",
                    error_code=error_code,
                    error_message_safe=error_message_safe[:512],
                    finished_at=now,
                )
            )
        connection.execute(
            update(self.t["index_jobs"]).where(
                self.t["index_jobs"].c.id == job["id"]
            ).values(
                state="failed",
                error_code=error_code,
                error_message_safe=error_message_safe[:512],
                finished_at=now,
            )
        )
        self._finish_version(connection, job, "failed", now)

    def _finish_version(
        self, connection, job, lifecycle: str, now: datetime
    ) -> None:
        if not job["target_index_version_id"]:
            return
        versions = self.t["index_versions"]
        connection.execute(
            update(versions).where(
                versions.c.id == job["target_index_version_id"],
                versions.c.lifecycle.in_(("building", "validating")),
            ).values(lifecycle=lifecycle, finished_at=now)
        )
