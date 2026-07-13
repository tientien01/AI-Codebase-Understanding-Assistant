# Job Queue Integration Report

Status: Verified JOB-003 local integration evidence

Verified: 2026-07-13

Profile: Python 3.11.9; PostgreSQL 18.4; Redis 8.2.7; Dramatiq 2.2.0; one worker thread

## Implemented boundary

- Production background submission persists the compatibility job as `queued` before publishing.
- Dramatiq messages use the fixed `aca.process_index_job` actor and `aca-indexing` queue with exactly one validated string `job_id` and no kwargs.
- Broker failures become `INDEX_QUEUE_UNAVAILABLE`/503 and include only the durable job ID plus `retryable=true`; the PostgreSQL row remains queued.
- The dedicated worker composes its database/application services after process fork, conditionally transitions `queued` to `running`, and reloads repository/job state before executing the current indexing pipeline.
- Actor automatic retries are disabled. PostgreSQL state remains authoritative.

## Verification results

| Gate | Result |
| --- | --- |
| Queue and persistence suites | 19 passed |
| Full backend regression | 86 passed |
| Concurrent duplicate delivery | One `started`, one `duplicate`, runner called once |
| Broker outage | Publication raised stable error; persisted state remained `queued` |
| Worker restart | Job queued before first start and job queued while stopped were both consumed in order |
| Worker actor composition | Fixed actor/queue and `max_retries=0` import smoke passed |
| Dependency lock | Dramatiq 2.2.0, redis-py 8.0.1, and conditional async-timeout hashes resolved reproducibly |

The full suite emitted the existing duplicate-ZIP warning and an OpenTelemetry dependency deprecation warning; neither is introduced behavior failure.

## Commands

```powershell
docker compose -f compose.integration.yml up -d postgres redis
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
$env:TEST_REDIS_URL='redis://127.0.0.1:56379/15'
backend\.venv\Scripts\python.exe -m pytest tests/jobs tests/persistence -q
backend\.venv\Scripts\python.exe -m pytest tests -q
backend\.venv\Scripts\uv.exe pip compile backend/requirements.txt --python-version 3.11 --universal --generate-hashes --output-file backend/requirements-lock.txt
git diff --check
docker compose -f compose.integration.yml down
```

## Remaining boundary

JOB-003 intentionally has no attempt lease, heartbeat, retry classification, durable cancellation, or stale-running recovery. If a worker dies after the `queued`-to-`running` transition, redelivery is acknowledged as a duplicate and the row remains running until JOB-004 adds fenced recovery. This limitation prevents a production-readiness claim but keeps this task inside its authorized scope.
