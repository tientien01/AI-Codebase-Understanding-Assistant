"""Persisted duplicate-delivery gate used by the dedicated worker."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from app.services.indexing.job_queue import validate_job_id
from app.services.indexing.job_state_store import JobStateStore, StateTransitionError


class PersistedIndexJobRunner(Protocol):
    def execute_persisted_job(self, job_id: str, repository_id: str) -> None: ...


class DeliveryDisposition(str, Enum):
    STARTED = "started"
    DUPLICATE = "duplicate"


class JobDeliveryError(RuntimeError):
    pass


class JobDeliveryService:
    def __init__(self, state: JobStateStore, runner: PersistedIndexJobRunner) -> None:
        self.state = state
        self.runner = runner

    def deliver(self, job_id: str) -> DeliveryDisposition:
        job_id = validate_job_id(job_id)
        repository_id = self.state.job_repository_id(job_id)
        if repository_id is None:
            raise JobDeliveryError("Delivered index job does not exist")

        current = self.state.job_state(job_id)
        if current != "queued":
            return DeliveryDisposition.DUPLICATE
        try:
            self.state.transition_job(job_id, "queued", "running")
        except StateTransitionError:
            if self.state.job_state(job_id) != "queued":
                return DeliveryDisposition.DUPLICATE
            raise

        self.runner.execute_persisted_job(job_id, repository_id)
        return DeliveryDisposition.STARTED
