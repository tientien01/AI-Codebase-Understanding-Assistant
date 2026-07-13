from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import time

from dramatiq import Actor, Worker
from dramatiq.brokers.redis import RedisBroker
import pytest
from redis import Redis
from sqlalchemy import insert

from app.core.errors import DomainError
from app.services.index_models import IndexingJobRecord, RepositoryState
from app.services.indexing.indexing_service import IndexingService
from app.services.indexing.job_delivery_service import (
    DeliveryDisposition,
    JobDeliveryService,
)
from app.services.indexing.job_queue import (
    DramatiqIndexJobQueue,
    INDEX_JOB_ACTOR,
    INDEX_JOB_QUEUE,
    QueueUnavailableError,
)
from app.services.indexing.job_state_store import JobStateStore, JobSubmission
from app.db.production_base import ProductionBase
import app.db.production_models  # noqa: F401


DIGEST = "b" * 64


class RecordingBroker:
    def __init__(self) -> None:
        self.message = None
        self.delay = None

    def enqueue(self, message, *, delay=None):
        self.message = message
        self.delay = delay
        return message


class UnavailableQueue:
    def enqueue(self, _job_id: str, *, delay_ms: int = 0) -> str:
        raise QueueUnavailableError("unavailable")


@dataclass
class RecordingRunner:
    calls: list[tuple[str, str]]

    def execute_persisted_job(self, job_id: str, repository_id: str, authority_check=None) -> None:
        if authority_check is not None:
            authority_check()
        self.calls.append((job_id, repository_id))


def _seed_job(engine, suffix: str = "queue") -> tuple[JobStateStore, dict[str, str]]:
    t = ProductionBase.metadata.tables
    ids = {
        "principal": f"principal_{suffix}",
        "repository": f"repo_{suffix}",
        "source": f"source_{suffix}",
        "snapshot": f"snapshot_{suffix}",
        "idem": f"idem_{suffix}",
        "job": f"job_{suffix}",
        "version": f"idx_{suffix}",
    }
    with engine.begin() as connection:
        connection.execute(
            insert(t["operator_principals"]).values(
                id=ids["principal"], display_name="Queue test"
            )
        )
        connection.execute(
            insert(t["repositories"]).values(
                id=ids["repository"],
                owner_principal_id=ids["principal"],
                display_name="Queue test",
            )
        )
        connection.execute(
            insert(t["repository_sources"]).values(
                id=ids["source"],
                repository_id=ids["repository"],
                source_type="upload_folder",
            )
        )
        connection.execute(
            insert(t["source_snapshots"]).values(
                id=ids["snapshot"],
                repository_id=ids["repository"],
                repository_source_id=ids["source"],
                storage_key=f"repositories/{ids['repository']}/source",
                snapshot_sha256=DIGEST,
                policy_version="1",
                inventory_schema_version="1",
                total_files=0,
                total_bytes=0,
            )
        )
    store = JobStateStore(engine)
    store.submit(
        JobSubmission(
            job_id=ids["job"],
            repository_id=ids["repository"],
            source_snapshot_id=ids["snapshot"],
            version_id=ids["version"],
            version_number=1,
            principal_id=ids["principal"],
            idempotency_record_id=ids["idem"],
            idempotency_key=ids["job"],
            request_sha256=DIGEST,
        )
    )
    return store, ids


def test_adapter_publishes_only_one_valid_job_id() -> None:
    broker = RecordingBroker()
    message_id = DramatiqIndexJobQueue(broker).enqueue("job_payload")

    assert message_id == broker.message.message_id
    assert broker.message.actor_name == INDEX_JOB_ACTOR
    assert broker.message.queue_name == INDEX_JOB_QUEUE
    assert broker.message.args == ("job_payload",)
    assert broker.message.kwargs == {}
    with pytest.raises(ValueError, match="opaque"):
        DramatiqIndexJobQueue(broker).enqueue("not-a-job")


def test_duplicate_delivery_starts_persisted_job_once(production_database) -> None:
    _, engine, _ = production_database
    state, ids = _seed_job(engine)
    runner = RecordingRunner([])
    delivery = JobDeliveryService(state, runner)

    with ThreadPoolExecutor(max_workers=2) as pool:
        dispositions = list(pool.map(lambda _: delivery.deliver(ids["job"]), range(2)))
    assert dispositions.count(DeliveryDisposition.STARTED) == 1
    assert dispositions.count(DeliveryDisposition.DUPLICATE) == 1
    assert runner.calls == [(ids["job"], ids["repository"])]
    assert state.job_state(ids["job"]) == "succeeded"


def test_broker_outage_preserves_queued_job(production_database) -> None:
    _, engine, _ = production_database
    state, ids = _seed_job(engine, "outage")
    broker = RedisBroker(
        url="redis://127.0.0.1:6399/0", socket_connect_timeout=0.1
    )

    with pytest.raises(QueueUnavailableError, match="unavailable"):
        DramatiqIndexJobQueue(broker).enqueue(ids["job"])
    assert state.job_state(ids["job"]) == "queued"


def test_background_publication_failure_returns_stable_error(monkeypatch) -> None:
    service = object.__new__(IndexingService)
    service.job_queue = UnavailableQueue()
    repository = RepositoryState(
        id="repo_queue", name="Queue", source_type="upload_folder", source_uri=None,
        source_path=Path.cwd(),
    )
    job = IndexingJobRecord(id="job_queue", repository_id=repository.id, status="queued")
    monkeypatch.setattr(
        service,
        "_prepare_indexing_job",
        lambda *_args, **_kwargs: (repository, job, None, "created"),
    )

    with pytest.raises(DomainError) as caught:
        service.start_indexing_background(repository.id)
    assert caught.value.code == "INDEX_QUEUE_UNAVAILABLE"
    assert caught.value.status_code == 503
    assert caught.value.details == {"job_id": job.id, "retryable": True}


def test_redis_worker_consumes_before_and_after_restart() -> None:
    redis_url = os.environ.get("TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("TEST_REDIS_URL is required")
    client = Redis.from_url(redis_url)
    client.flushdb()
    namespace = "aca-job003-test"
    broker = RedisBroker(url=redis_url, namespace=namespace)
    received_key = f"{namespace}:received"

    def record(job_id: str) -> None:
        client.rpush(received_key, job_id)

    actor = Actor(
        record,
        broker=broker,
        actor_name=INDEX_JOB_ACTOR,
        queue_name=INDEX_JOB_QUEUE,
        priority=0,
        options={"max_retries": 0},
    )
    broker.declare_actor(actor)
    queue = DramatiqIndexJobQueue(broker)

    queue.enqueue("job_before_start")
    first = Worker(broker, worker_threads=1)
    first.start()
    _wait_for_values(client, received_key, ["job_before_start"])
    first.stop(timeout=5_000)
    first.join()

    queue.enqueue("job_after_stop")
    second = Worker(broker, worker_threads=1)
    second.start()
    _wait_for_values(
        client, received_key, ["job_before_start", "job_after_stop"]
    )
    second.stop(timeout=5_000)
    second.join()
    assert [item.decode() for item in client.lrange(received_key, 0, -1)] == [
        "job_before_start",
        "job_after_stop",
    ]


def _wait_for_values(client: Redis, key: str, expected: list[str]) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        values = [item.decode() for item in client.lrange(key, 0, -1)]
        if values == expected:
            return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {expected!r}")
