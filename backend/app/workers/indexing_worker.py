"""Dramatiq composition root for persisted index-job delivery."""

from __future__ import annotations

from functools import lru_cache
from uuid import uuid4

import dramatiq

from app.core.config import settings
from app.services.application.container import ApplicationContainer
from app.services.indexing.job_delivery_service import JobDeliveryService
from app.services.indexing.job_queue import (
    DramatiqIndexJobQueue,
    INDEX_JOB_ACTOR,
    INDEX_JOB_QUEUE,
    create_dramatiq_broker,
)
from app.services.repositories.production_repository_store import ProductionRepositoryStore


broker = create_dramatiq_broker(settings.redis_url)
dramatiq.set_broker(broker)


@lru_cache(maxsize=1)
def _delivery_service() -> JobDeliveryService:
    """Compose after worker fork so DB pools are never inherited."""
    container = ApplicationContainer()
    if (
        not isinstance(container.store, ProductionRepositoryStore)
        or container.job_state_store is None
    ):
        raise RuntimeError("The dedicated indexing worker requires APP_ENV=production")
    return JobDeliveryService(
        container.job_state_store,
        container.indexing,
        queue=DramatiqIndexJobQueue(broker),
        worker_id=f"worker_{uuid4().hex}",
        lease_seconds=settings.index_lease_seconds,
        heartbeat_seconds=settings.index_heartbeat_seconds,
        max_attempts=settings.index_max_attempts,
    )


@dramatiq.actor(
    actor_name=INDEX_JOB_ACTOR,
    queue_name=INDEX_JOB_QUEUE,
    max_retries=0,
)
def process_index_job(job_id: str) -> str:
    return _delivery_service().deliver(job_id).value
