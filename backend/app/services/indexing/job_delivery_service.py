"""Fenced delivery, heartbeat, retry, cancellation, and stale-lease recovery."""

from __future__ import annotations

from enum import Enum
from threading import Event, Thread
from typing import Callable, Protocol

from app.services.indexing.indexing_service import (
    IndexingAuthorityLost,
    IndexingCancelled,
)
from app.services.indexing.job_queue import (
    IndexJobQueuePort,
    QueueUnavailableError,
    validate_job_id,
)
from app.services.indexing.job_state_store import (
    CancellationRequested,
    ClaimDisposition,
    JobLease,
    JobStateStore,
    LeaseLostError,
    StateTransitionError,
)


class PersistedIndexJobRunner(Protocol):
    def execute_persisted_job(
        self,
        job_id: str,
        repository_id: str,
        authority_check: Callable[[], None] | None = None,
    ) -> None: ...


class DeliveryDisposition(str, Enum):
    STARTED = "started"
    DUPLICATE = "duplicate"
    RECOVERY_SCHEDULED = "recovery_scheduled"
    RETRY_SCHEDULED = "retry_scheduled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    LEASE_LOST = "lease_lost"


class JobDeliveryError(RuntimeError):
    pass


class RetryableJobError(RuntimeError):
    """Explicitly marks an infrastructure failure as safe to retry."""


class LeaseHeartbeatMonitor:
    """Refresh a lease and expose cooperative cancellation at safe boundaries."""

    def __init__(
        self,
        state: JobStateStore,
        lease: JobLease,
        *,
        heartbeat_seconds: int,
        lease_seconds: int,
    ) -> None:
        self.state = state
        self.lease = lease
        self.heartbeat_seconds = heartbeat_seconds
        self.lease_seconds = lease_seconds
        self._stop = Event()
        self._cancelled = Event()
        self._lost = Event()
        self._thread = Thread(target=self._run, name=f"lease-{lease.attempt_id}", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=max(self.heartbeat_seconds * 2, 1))

    def check(self) -> None:
        if self._cancelled.is_set():
            raise IndexingCancelled()
        if self._lost.is_set():
            raise IndexingAuthorityLost()

    def _run(self) -> None:
        while not self._stop.wait(self.heartbeat_seconds):
            try:
                self.lease = self.state.heartbeat(
                    self.lease, lease_seconds=self.lease_seconds
                )
            except CancellationRequested:
                self._cancelled.set()
                return
            except LeaseLostError:
                self._lost.set()
                return
            except Exception:  # DB loss also revokes local authority.
                self._lost.set()
                return


class JobDeliveryService:
    def __init__(
        self,
        state: JobStateStore,
        runner: PersistedIndexJobRunner,
        *,
        queue: IndexJobQueuePort | None = None,
        worker_id: str = "worker_test",
        lease_seconds: int = 60,
        heartbeat_seconds: int = 15,
        max_attempts: int = 3,
    ) -> None:
        self.state = state
        self.runner = runner
        self.queue = queue
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.max_attempts = max_attempts

    def deliver(self, job_id: str) -> DeliveryDisposition:
        job_id = validate_job_id(job_id)
        try:
            claim = self.state.claim(
                job_id,
                self.worker_id,
                lease_seconds=self.lease_seconds,
                max_attempts=self.max_attempts,
            )
        except StateTransitionError as exc:
            raise JobDeliveryError("Delivered index job does not exist") from exc

        if claim.disposition is ClaimDisposition.TERMINAL:
            return DeliveryDisposition.DUPLICATE
        if claim.disposition is ClaimDisposition.DEFERRED:
            if self.queue is None:
                return DeliveryDisposition.DUPLICATE
            delay_ms = max(1, int((claim.retry_after_seconds or 0) * 1000) + 50)
            try:
                self.queue.enqueue(job_id, delay_ms=delay_ms)
            except QueueUnavailableError:
                return DeliveryDisposition.DUPLICATE
            return DeliveryDisposition.RECOVERY_SCHEDULED

        lease = claim.lease
        if lease is None:  # Defensive: a claimed disposition must always own a lease.
            raise JobDeliveryError("Claimed index job has no lease")
        monitor = LeaseHeartbeatMonitor(
            self.state,
            lease,
            heartbeat_seconds=self.heartbeat_seconds,
            lease_seconds=self.lease_seconds,
        )
        monitor.start()
        try:
            self.runner.execute_persisted_job(
                job_id, lease.repository_id, monitor.check
            )
            monitor.stop()
            monitor.check()
            self.state.complete(lease)
            return DeliveryDisposition.STARTED
        except (IndexingCancelled, CancellationRequested):
            monitor.stop()
            try:
                self.state.cancel(lease)
            except LeaseLostError:
                return DeliveryDisposition.LEASE_LOST
            return DeliveryDisposition.CANCELLED
        except (IndexingAuthorityLost, LeaseLostError):
            monitor.stop()
            return DeliveryDisposition.LEASE_LOST
        except Exception as exc:
            monitor.stop()
            retryable = isinstance(exc, (RetryableJobError, TimeoutError, ConnectionError))
            try:
                should_retry = self.state.fail(
                    lease,
                    retryable=retryable,
                    max_attempts=self.max_attempts,
                    error_code="TRANSIENT_INDEXING_FAILURE" if retryable else "INDEXING_FAILED",
                    error_message_safe="Indexing dependency failed." if retryable else "Indexing failed.",
                )
            except (LeaseLostError, CancellationRequested):
                return DeliveryDisposition.LEASE_LOST
            if not should_retry:
                return DeliveryDisposition.FAILED
            if self.queue is None:
                return DeliveryDisposition.RETRY_SCHEDULED
            delay_ms = min(60_000, 1000 * (2 ** (lease.generation - 1)))
            try:
                self.queue.enqueue(job_id, delay_ms=delay_ms)
            except QueueUnavailableError:
                # PostgreSQL remains queued for the idempotent redispatch path.
                pass
            return DeliveryDisposition.RETRY_SCHEDULED
        finally:
            monitor.stop()
