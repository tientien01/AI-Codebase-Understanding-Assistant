from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
import time

from dramatiq import Actor, Worker
from dramatiq.brokers.redis import RedisBroker
import pytest
from redis import Redis

from app.services.indexing.job_delivery_service import JobDeliveryService
from app.services.indexing.job_queue import (
    DramatiqIndexJobQueue,
    INDEX_JOB_ACTOR,
    INDEX_JOB_QUEUE,
)
from app.services.indexing.job_state_store import (
    CancellationRequested,
    ClaimDisposition,
    JobStateStore,
    LeaseLostError,
)
from tests.jobs.test_job_queue import RecordingRunner, _seed_job


def test_claim_heartbeat_and_duplicate_delivery_are_fenced(production_database) -> None:
    _, engine, _ = production_database
    state, ids = _seed_job(engine, "claim")
    started = datetime(2026, 7, 13, tzinfo=UTC)

    first = state.claim(
        ids["job"], "worker_one", lease_seconds=30, max_attempts=3, now=started
    )
    duplicate = state.claim(
        ids["job"], "worker_two", lease_seconds=30, max_attempts=3, now=started
    )

    assert first.disposition is ClaimDisposition.CLAIMED
    assert first.lease is not None
    assert duplicate.disposition is ClaimDisposition.DEFERRED
    extended = state.heartbeat(
        first.lease, lease_seconds=30, now=started + timedelta(seconds=10)
    )
    assert extended.lease_expires_at == started + timedelta(seconds=40)
    details = state.job_details(ids["job"])
    assert details["lease_generation"] == 1
    assert details["current_attempt_id"] == first.lease.attempt_id


def test_expired_attempt_is_replaced_and_old_generation_cannot_finish(production_database) -> None:
    _, engine, _ = production_database
    state, ids = _seed_job(engine, "stale")
    started = datetime(2026, 7, 13, tzinfo=UTC)
    first = state.claim(
        ids["job"], "worker_old", lease_seconds=5, max_attempts=3, now=started
    ).lease
    assert first is not None

    replacement = state.claim(
        ids["job"],
        "worker_new",
        lease_seconds=5,
        max_attempts=3,
        now=started + timedelta(seconds=6),
    ).lease
    assert replacement is not None
    assert replacement.generation == 2
    assert state.attempt_details(first.attempt_id)["state"] == "lease_lost"
    with pytest.raises(LeaseLostError, match="LEASE_LOST"):
        state.complete(first, now=started + timedelta(seconds=7))
    assert state.complete(replacement, now=started + timedelta(seconds=7)) == "succeeded"


def test_durable_cancellation_stops_queued_and_running_jobs(production_database) -> None:
    _, engine, _ = production_database
    state, queued_ids = _seed_job(engine, "cancel_queued")
    assert state.request_cancellation(queued_ids["job"]) == "cancelled"
    assert state.job_state(queued_ids["job"]) == "cancelled"

    state, running_ids = _seed_job(engine, "cancel_running")
    lease = state.claim(
        running_ids["job"], "worker_cancel", lease_seconds=30, max_attempts=3
    ).lease
    assert lease is not None
    assert state.request_cancellation(running_ids["job"]) == "running"
    with pytest.raises(CancellationRequested):
        state.heartbeat(lease, lease_seconds=30)
    state.cancel(lease)
    assert state.job_state(running_ids["job"]) == "cancelled"


def test_retry_budget_is_persisted_and_bounded(production_database) -> None:
    _, engine, _ = production_database
    state, ids = _seed_job(engine, "retry")
    first = state.claim(
        ids["job"], "worker_one", lease_seconds=30, max_attempts=2
    ).lease
    assert first is not None
    assert state.fail(
        first,
        retryable=True,
        max_attempts=2,
        error_code="TRANSIENT_INDEXING_FAILURE",
        error_message_safe="Dependency unavailable.",
    ) is True
    assert state.job_state(ids["job"]) == "queued"

    second = state.claim(
        ids["job"], "worker_two", lease_seconds=30, max_attempts=2
    ).lease
    assert second is not None and second.generation == 2
    assert state.fail(
        second,
        retryable=True,
        max_attempts=2,
        error_code="TRANSIENT_INDEXING_FAILURE",
        error_message_safe="Dependency unavailable.",
    ) is False
    assert state.job_state(ids["job"]) == "failed"


def test_redis_redelivery_recovers_worker_lost_after_claim(production_database) -> None:
    redis_url = os.environ.get("TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("TEST_REDIS_URL is required")
    _, engine, _ = production_database
    state, ids = _seed_job(engine, "worker_loss")
    client = Redis.from_url(redis_url)
    client.flushdb()
    namespace = "aca-job004-worker-loss"
    broker = RedisBroker(url=redis_url, namespace=namespace)
    queue = DramatiqIndexJobQueue(broker)
    runner = RecordingRunner([])
    delivery = JobDeliveryService(
        state,
        runner,
        queue=queue,
        worker_id="worker_replacement",
        lease_seconds=2,
        heartbeat_seconds=1,
        max_attempts=3,
    )

    # The first worker disappeared after claiming and before acknowledging.
    original = state.claim(
        ids["job"], "worker_lost", lease_seconds=2, max_attempts=3
    ).lease
    assert original is not None

    def deliver(job_id: str) -> str:
        return delivery.deliver(job_id).value

    actor = Actor(
        deliver,
        broker=broker,
        actor_name=INDEX_JOB_ACTOR,
        queue_name=INDEX_JOB_QUEUE,
        priority=0,
        options={"max_retries": 0},
    )
    broker.declare_actor(actor)
    queue.enqueue(ids["job"])
    worker = Worker(broker, worker_threads=1)
    worker.start()
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and state.job_state(ids["job"]) != "succeeded":
            time.sleep(0.05)
        assert state.job_state(ids["job"]) == "succeeded"
        assert runner.calls == [(ids["job"], ids["repository"])]
        assert state.job_details(ids["job"])["lease_generation"] == 2
    finally:
        worker.stop(timeout=5_000)
        worker.join()
