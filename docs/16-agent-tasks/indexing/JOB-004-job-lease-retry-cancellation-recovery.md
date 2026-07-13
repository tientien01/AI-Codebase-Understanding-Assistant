---
id: JOB-004
title: Add fenced job leases, retry, cancellation, and recovery
status: completed
priority: P0
phase: 2
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [JOB-003]
requirements: []
contracts:
  - docs/04-domain-and-data/specifications/detailed-data-model.md
  - docs/04-domain-and-data/postgresql-physical-schema.md
  - docs/05-domain-contracts/indexing.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
decisions:
  - docs/13-decisions/ADR-0003-production-job-queue.md
technology_docs:
  - docs/03-technology/environment-and-configuration.md
  - docs/03-technology/stack-overview.md
  - docs/11-testing/specifications/detailed-testing-plan.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/core/config.py
  - backend/app/services/application/container.py
  - backend/app/services/indexing/indexing_service.py
  - backend/app/services/indexing/job_state_store.py
  - backend/app/services/indexing/job_queue.py
  - backend/app/services/indexing/job_delivery_service.py
  - backend/app/services/repositories/production_repository_store.py
  - backend/app/workers/indexing_worker.py
  - tests/jobs/**
  - tests/persistence/test_production_repository.py
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/indexing/JOB-004-job-lease-retry-cancellation-recovery.md
  - docs/17-runbooks/stuck-index-job.md
  - docs/18-production-evidence/job-resilience-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/migrations/**
  - backend/app/db/models.py
  - backend/app/db/production_models/**
  - backend/app/api/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - A claim atomically increments lease_generation, creates one attempt, and fences every heartbeat and terminal write by job, attempt, generation, running state, repository generation, cancellation boundary, and lease expiry.
  - A stale worker receives LEASE_LOST and cannot commit a checkpoint, terminal transition, or retry after a replacement claim.
  - Heartbeats extend only the current unexpired lease and worker execution stops cooperatively after lease loss or durable cancellation.
  - Transient failures consume a persisted bounded attempt budget and redispatch with bounded backoff; permanent failures become terminal without redispatch.
  - Expired running attempts recover idempotently through a new generation, while duplicate, early, or terminal deliveries do not execute a second authoritative attempt.
  - Local and test indexing retain the existing in-process behavior without PostgreSQL or Redis.
evidence_outputs:
  - docs/18-production-evidence/job-resilience-report.md
---

# Task JOB-004 — Add fenced job leases, retry, cancellation, and recovery

## Context

JOB-003 moved production delivery to a dedicated Dramatiq worker but deliberately transitions a queued job directly to running without a persisted attempt lease. A worker crash after that transition leaves the job unrecoverable, and production cancellation, retry ownership, and stale-worker fencing are not yet enforced.

## Objective

Make production index-job execution recoverable and single-authority under duplicate delivery, worker loss, retryable failure, and cancellation by enforcing the accepted PostgreSQL attempt/lease model without changing the existing schema or local execution profile.

## In scope

- Validated lease, heartbeat, and maximum-attempt production settings.
- Atomic job claim that increments the fencing generation and creates the authoritative attempt.
- Conditional heartbeat, cancellation observation, attempt completion, terminal failure, and retry transitions.
- A worker-side heartbeat/cancellation monitor that stops accepting authoritative completion after lease loss.
- Persistent transient/permanent error classification, bounded backoff redispatch, and expired-lease recovery.
- PostgreSQL/Redis resilience tests for stale fencing, worker loss, retry exhaustion, cancellation, and duplicate delivery.

## Out of scope

Schema or migration changes, HTTP/OpenAPI shape changes, repository deletion fencing, typed indexing-stage/checkpoint artifacts, immutable artifact publication, atomic index activation, new telemetry exporters, production containers, and frontend work.

## Existing code to reuse

- The `index_jobs` and `job_attempts` tables and recovery indexes created by DAT-002.
- `JobStateStore`, `JobDeliveryService`, and the one-ID Dramatiq adapter/worker from JOB-003.
- `IndexingService.execute_persisted_job` and its current local/test-compatible indexing path.
- `ProductionRepositoryStore.save_indexing_job`, with compatibility progress writes narrowed so they cannot overwrite lease authority.
- The PostgreSQL/Redis fixtures under `tests/jobs/`.

## Implementation sequence

1. Add positive, ordered lease/heartbeat/attempt settings and reject unsafe production values.
2. Replace the queued-to-running delivery gate with one atomic claim that creates an attempt and fencing generation.
3. Add fenced heartbeat, cancellation observation, success/failure, retry, and expired-lease recovery commands.
4. Preserve lease-owned columns when the compatibility adapter writes pipeline progress, run worker execution behind a heartbeat/cancellation monitor, and reject completion after lease loss.
5. Classify failures, persist bounded retry state, and redispatch only retryable jobs with bounded delay.
6. Add deterministic PostgreSQL tests and a Redis worker-loss recovery test, then record the exact evidence.

## Data/API compatibility and migration

No migration is allowed: the accepted production schema already contains every required job and attempt field and recovery index. Queue payloads remain exactly one opaque job ID. HTTP response shapes do not change. Local/test execution remains in process; only the production PostgreSQL/Redis worker path gains lease semantics.

## Failure, security, performance, and observability requirements

- Worker IDs and attempt IDs are opaque generated identifiers and are never returned to ordinary clients or included in safe errors.
- Lease ownership uses `lease_generation`; timestamps or worker identity alone never authorize a write.
- Heartbeat must be shorter than the lease and must stop promptly after cancellation, lease loss, or worker completion.
- Only explicitly retryable dependency/time-limit failures consume the retry path; validation, authorization, missing-record, and other permanent failures terminate immediately.
- Retry delay is bounded and derived from persisted attempt count. No Dramatiq actor-level automatic retry is enabled.
- A failure to redispatch leaves an observable queued database row for the existing idempotent redispatch path.

## Required tests and commands

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

The PostgreSQL/Redis commands use only the disposable integration services declared by `compose.integration.yml`. The exact results and environment identity are recorded in `docs/18-production-evidence/job-resilience-report.md`.

## Acceptance criteria

- Two concurrent claims of one queued job create exactly one current attempt and increment generation once.
- A current heartbeat extends its lease; a stale generation, expired lease, cancellation request, or repository-generation mismatch returns `LEASE_LOST` without mutation.
- A replacement claim after expiry prevents the old attempt from completing or scheduling retry.
- A durable cancellation request stops a queued job immediately or causes the running attempt to finish cancelled at its next cooperative check.
- Retryable failures create at most `INDEX_MAX_ATTEMPTS` attempts with bounded redispatch delay; permanent failures and exhausted attempts become terminal.
- Duplicate/early/terminal deliveries do not invoke the index runner twice, and a worker-loss integration case recovers after lease expiry.
- Targeted jobs, persistence integration, full backend regression, and diff hygiene commands pass.

## Rollback

Stop workers, restore JOB-003 delivery behavior, and retain queued/running job and attempt rows for operator diagnosis. No schema or authoritative payload migration is required. Do not resume production workers until stale running rows are cancelled or safely redispatched by the restored version.

## Documentation and evidence updates

All required commands passed. The source/test baselines, stuck-job runbook, resilience report, and project status now advance the documented next candidate to `IDX-001` without claiming Phase 2 or production completion.
