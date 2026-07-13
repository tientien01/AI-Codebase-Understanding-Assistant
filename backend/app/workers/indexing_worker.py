"""Dramatiq composition root for persisted index-job delivery."""

from __future__ import annotations

from functools import lru_cache

import dramatiq

from app.core.config import settings
from app.services.application.container import ApplicationContainer
from app.services.indexing.job_delivery_service import JobDeliveryService
from app.services.indexing.job_queue import (
    INDEX_JOB_ACTOR,
    INDEX_JOB_QUEUE,
    create_dramatiq_broker,
)
from app.services.indexing.job_state_store import JobStateStore
from app.services.repositories.production_repository_store import ProductionRepositoryStore


broker = create_dramatiq_broker(settings.redis_url)
dramatiq.set_broker(broker)


@lru_cache(maxsize=1)
def _delivery_service() -> JobDeliveryService:
    """Compose after worker fork so DB pools are never inherited."""
    container = ApplicationContainer()
    if not isinstance(container.store, ProductionRepositoryStore):
        raise RuntimeError("The dedicated indexing worker requires APP_ENV=production")
    return JobDeliveryService(JobStateStore(container.store.engine), container.indexing)


@dramatiq.actor(
    actor_name=INDEX_JOB_ACTOR,
    queue_name=INDEX_JOB_QUEUE,
    max_retries=0,
)
def process_index_job(job_id: str) -> str:
    return _delivery_service().deliver(job_id).value
