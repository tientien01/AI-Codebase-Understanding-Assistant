# Job Resilience Report

Status: Verified JOB-004 local integration evidence

Verified: 2026-07-13

Profile: Python 3.11.9; PostgreSQL 18.4; Redis 8.2.7; Dramatiq 2.2.0; one worker thread

## Implemented boundary

- PostgreSQL atomically locks a job/repository, increments `lease_generation`, creates the current `job_attempts` row, and records an opaque worker identity.
- Heartbeat and completion re-check job, attempt, generation, running state, unexpired lease, repository operation generation, lifecycle, and cancellation state.
- Durable cancellation immediately terminates queued jobs or is observed cooperatively by running workers at safe pipeline boundaries.
- Expired attempts become `lease_lost`; Redis redelivery creates a replacement generation and the old generation cannot complete.
- Explicit transient failures consume the persisted attempt budget and redispatch with bounded exponential delay. Permanent or exhausted failures become terminal without actor-level automatic retry.
- Compatibility progress writes preserve `current_attempt_id`, lease/repository generations, terminal authority, and safe error fields while a dedicated-worker lease is active.

## Verification results

| Gate | Result |
| --- | --- |
| Job resilience suite | 14 passed |
| Persistence integration suite | 12 passed |
| Full backend regression | 93 passed |
| Concurrent claim | One current attempt and one deferred duplicate; generation incremented once |
| Heartbeat/fencing | Current lease extended; expired/replaced generation returned `LEASE_LOST` |
| Durable cancellation | Queued job terminated immediately; running heartbeat observed cancellation and completed cancelled |
| Bounded retry | Retryable failure requeued until the persisted two-attempt budget, then terminated failed |
| Worker loss | Redis delivery deferred until lease expiry, replacement attempt succeeded at generation 2 |
| Compatibility adapter | Progress write preserved running state, generation, and current attempt |

The full suite emitted the existing duplicate-ZIP warning and an OpenTelemetry dependency deprecation warning; neither is an introduced behavior failure.

## Commands

```powershell
docker compose -f compose.integration.yml up -d postgres redis
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
$env:TEST_REDIS_URL='redis://127.0.0.1:56379/15'
backend\.venv\Scripts\python.exe -m pytest tests/jobs -q
backend\.venv\Scripts\python.exe -m pytest tests/persistence -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
docker compose -f compose.integration.yml down
```

## Remaining boundary

JOB-004 verifies job/attempt authority and cooperative safe-boundary checks. Immutable stage artifacts, checkpoint validation, manifest publication, and transactional index activation remain owned by `IDX-001` through `IDX-003`. This report is task evidence, not Phase 2 or production-release evidence.
