"""Typed queue boundary for opaque persisted index-job IDs."""

from __future__ import annotations

import re
from typing import Protocol

from dramatiq import Message
from dramatiq.broker import Broker
from dramatiq.brokers.redis import RedisBroker
from dramatiq.errors import BrokerConnectionError
from redis.exceptions import RedisError


INDEX_JOB_ACTOR = "aca.process_index_job"
INDEX_JOB_QUEUE = "aca-indexing"
JOB_ID = re.compile(r"^job_[A-Za-z0-9][A-Za-z0-9_-]*$")


class QueueUnavailableError(RuntimeError):
    """Stable publication failure that does not expose broker configuration."""


class IndexJobQueuePort(Protocol):
    def enqueue(self, job_id: str, *, delay_ms: int = 0) -> str: ...


def validate_job_id(job_id: str) -> str:
    if len(job_id) > 128 or not JOB_ID.fullmatch(job_id):
        raise ValueError("job_id must be a valid opaque index-job ID")
    return job_id


def create_dramatiq_broker(redis_url: str, *, namespace: str = "aca") -> RedisBroker:
    if not redis_url.startswith(("redis://", "rediss://")):
        raise ValueError("A Redis URL is required for the Dramatiq broker")
    return RedisBroker(url=redis_url, namespace=namespace)


class DramatiqIndexJobQueue:
    """Publish one JSON-safe ID; PostgreSQL owns every other job field."""

    def __init__(self, broker: Broker) -> None:
        self.broker = broker

    def enqueue(self, job_id: str, *, delay_ms: int = 0) -> str:
        if delay_ms < 0:
            raise ValueError("delay_ms must be non-negative")
        message = Message(
            queue_name=INDEX_JOB_QUEUE,
            actor_name=INDEX_JOB_ACTOR,
            args=(validate_job_id(job_id),),
            kwargs={},
            options={},
        )
        try:
            published = self.broker.enqueue(message, delay=delay_ms or None)
        except (BrokerConnectionError, RedisError) as exc:
            raise QueueUnavailableError("Index job queue is unavailable") from exc
        return published.message_id
