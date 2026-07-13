"""Dramatiq candidate configured for prompt crash recovery in the PoC."""

from __future__ import annotations

import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from state import execute_job


broker = RedisBroker(
    url=os.environ["REDIS_URL"],
    namespace="aca-dramatiq-poc",
    heartbeat_timeout=2_000,
    maintenance_chance=1_000_000,
)
dramatiq.set_broker(broker)


@dramatiq.actor(queue_name="aca", max_retries=0)
def process_job(job_id: str) -> str:
    return execute_job(job_id)
