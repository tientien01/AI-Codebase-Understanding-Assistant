"""Run equivalent correctness scenarios against RQ and Dramatiq."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Callable

import dramatiq
from dramatiq import Message
from dramatiq.brokers.redis import RedisBroker
from redis import Redis
from rq import Queue, Retry
from rq.job import Job
from rq.serializers import JSONSerializer

from state import initialize, request_cancel, reset_job, snapshot


REDIS_URL = os.environ["REDIS_URL"]
TIMEOUT_SECONDS = 30.0
RUNS = 3


@dataclass(frozen=True)
class Result:
    candidate: str
    run: int
    scenario: str
    passed: bool
    elapsed_ms: int
    detail: str


class Candidate:
    def __init__(self, name: str) -> None:
        self.name = name
        self.redis = Redis.from_url(REDIS_URL)

    def enqueue(self, job_id: str):
        if self.name == "rq":
            queue = Queue("aca", connection=self.redis, serializer=JSONSerializer)
            return queue.enqueue(
                "state.execute_job",
                job_id,
                job_id=f"rq-{job_id}",
                retry=Retry(max=1),
                job_timeout=60,
            )
        from dramatiq_tasks import process_job

        return process_job.send(job_id)

    def payload_is_job_id_only(self, message, job_id: str) -> bool:
        if self.name == "rq":
            job = Job.fetch(message.id, connection=self.redis, serializer=JSONSerializer)
            return list(job.args) == [job_id] and job.kwargs == {}
        return list(message.args) == [job_id] and message.kwargs == {}

    def worker_command(self) -> list[str]:
        if self.name == "rq":
            return [sys.executable, "rq_worker.py"]
        return [
            sys.executable,
            "-m",
            "dramatiq",
            "dramatiq_tasks",
            "--processes",
            "1",
            "--threads",
            "1",
        ]

    def assert_broker_outage(self, job_id: str) -> None:
        unavailable = "redis://127.0.0.1:6399/0"
        if self.name == "rq":
            Queue(
                "aca", connection=Redis.from_url(unavailable), serializer=JSONSerializer
            ).enqueue("state.execute_job", job_id, job_id=f"rq-{job_id}")
            return
        broker = RedisBroker(url=unavailable, socket_connect_timeout=0.5)
        broker.enqueue(
            Message(
                queue_name="aca",
                actor_name="process_job",
                args=(job_id,),
                kwargs={},
                options={},
            )
        )


def wait_for(job_id: str, predicate: Callable[[dict[str, object]], bool]) -> dict[str, object]:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        current = snapshot(job_id)
        if predicate(current):
            return current
        time.sleep(0.05)
    raise TimeoutError(f"Timed out waiting for {job_id}: {snapshot(job_id)}")


def start_worker(candidate: Candidate) -> subprocess.Popen[str]:
    return subprocess.Popen(
        candidate.worker_command(),
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def stop_worker(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        # RQ's work-horse may establish its own process group. Walk Linux procfs
        # so a forced-loss scenario terminates the worker and every descendant.
        descendants: list[int] = []

        def collect(pid: int) -> None:
            children_file = Path(f"/proc/{pid}/task/{pid}/children")
            if not children_file.exists():
                return
            for value in children_file.read_text(encoding="utf-8").split():
                child = int(value)
                collect(child)
                descendants.append(child)

        collect(process.pid)
        for pid in descendants:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def run_scenario(candidate: Candidate, run: int, scenario: str) -> Result:
    candidate.redis.flushdb()
    job_id = f"{candidate.name}-{run}-{scenario}"
    started = time.monotonic()
    detail = ""
    passed = False
    workers: list[subprocess.Popen[str]] = []
    try:
        if scenario == "json_payload":
            reset_job(job_id, 0.05)
            message = candidate.enqueue(job_id)
            passed = candidate.payload_is_job_id_only(message, job_id)
            detail = "decoded args contain only the opaque job ID"

        elif scenario == "worker_loss_recovery":
            reset_job(job_id, 1.0)
            candidate.enqueue(job_id)
            first = start_worker(candidate)
            workers.append(first)
            wait_for(job_id, lambda row: row["state"] == "running")
            stop_worker(first)
            second = start_worker(candidate)
            workers.append(second)
            final = wait_for(job_id, lambda row: row["state"] == "completed")
            passed = int(final["attempts"]) >= 2
            detail = f"replacement completed after {final['attempts']} attempts"

        elif scenario == "queued_cancellation":
            reset_job(job_id, 0.2, cancelled=True)
            candidate.enqueue(job_id)
            workers.append(start_worker(candidate))
            final = wait_for(job_id, lambda row: row["state"] == "cancelled")
            passed = int(final["attempts"]) == 0
            detail = "durable cancellation prevented work from starting"

        elif scenario == "running_cancellation":
            reset_job(job_id, 5.0)
            candidate.enqueue(job_id)
            workers.append(start_worker(candidate))
            wait_for(job_id, lambda row: row["state"] == "running")
            cancel_started = time.monotonic()
            request_cancel(job_id)
            final = wait_for(job_id, lambda row: row["state"] == "cancelled")
            cancellation_ms = int((time.monotonic() - cancel_started) * 1000)
            passed = cancellation_ms <= 2_000 and int(final["attempts"]) == 1
            detail = f"cooperative stop observed in {cancellation_ms} ms"

        elif scenario == "broker_outage":
            reset_job(job_id, 0.05)
            try:
                candidate.assert_broker_outage(job_id)
            except Exception as exc:  # Candidate-specific connection error types.
                current = snapshot(job_id)
                passed = current["state"] == "queued" and current["attempts"] == 0
                detail = f"submission raised {type(exc).__name__} without execution"
            else:
                detail = "submission unexpectedly succeeded"
        else:
            raise ValueError(scenario)
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
    finally:
        for worker in workers:
            stop_worker(worker)

    return Result(
        candidate=candidate.name,
        run=run,
        scenario=scenario,
        passed=passed,
        elapsed_ms=int((time.monotonic() - started) * 1000),
        detail=detail,
    )


def main() -> int:
    initialize()
    scenarios = (
        "json_payload",
        "worker_loss_recovery",
        "queued_cancellation",
        "running_cancellation",
        "broker_outage",
    )
    results = [
        run_scenario(Candidate(candidate), run, scenario)
        for candidate in ("rq", "dramatiq")
        for run in range(1, RUNS + 1)
        for scenario in scenarios
    ]
    payload = {
        "schema_version": "queue-poc/v1",
        "runs_per_scenario": RUNS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "results": [asdict(result) for result in results],
    }
    Path("results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for result in results:
        print(json.dumps(asdict(result), sort_keys=True))
    complete = len(results) == 30
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
