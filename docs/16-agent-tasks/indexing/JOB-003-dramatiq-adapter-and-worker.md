---
id: JOB-003
title: Add the Dramatiq queue adapter and dedicated indexing worker
status: completed
priority: P0
phase: 2
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [JOB-002]
requirements: []
contracts:
  - docs/05-domain-contracts/indexing.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
decisions:
  - docs/13-decisions/ADR-0003-production-job-queue.md
technology_docs:
  - docs/03-technology/environment-and-configuration.md
  - docs/03-technology/stack-overview.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - backend/app/core/config.py
  - backend/app/services/application/container.py
  - backend/app/services/indexing/indexing_service.py
  - backend/app/services/indexing/job_state_store.py
  - backend/app/services/indexing/job_queue.py
  - backend/app/services/indexing/job_delivery_service.py
  - backend/app/workers/**
  - tests/jobs/**
  - tests/persistence/test_production_repository.py
  - compose.integration.yml
  - .github/workflows/ci.yml
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/indexing/JOB-003-dramatiq-adapter-and-worker.md
  - docs/17-runbooks/development-setup.md
  - docs/18-production-evidence/job-queue-integration-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/migrations/**
  - backend/app/db/models.py
  - backend/app/db/production_models/**
  - backend/app/api/**
  - frontend/**
  - storage/**
dependency_changes:
  allowed: true
  add:
    - dramatiq[redis]==2.2.0
  remove: []
production_gates:
  - Production background submission publishes exactly one JSON-safe job ID to Dramatiq after the PostgreSQL job row is queued.
  - Broker publication failure returns a stable service error and leaves the PostgreSQL job queued for idempotent redispatch.
  - A dedicated one-thread worker reloads job/repository state and executes outside the API process.
  - Duplicate delivery starts the persisted job at most once; a worker restart consumes work queued while it was offline.
  - Local/test indexing keeps its current in-process behavior and does not require Redis.
  - Lease, heartbeat, persistent retry budget, durable cancellation, and stale-running recovery remain in JOB-004.
evidence_outputs:
  - docs/18-production-evidence/job-queue-integration-report.md
---

# Task JOB-003 — Add the Dramatiq queue adapter and dedicated indexing worker

## Objective

Introduce the accepted Dramatiq dependency, a typed job-ID queue boundary, production background dispatch, and a dedicated worker composition root without weakening PostgreSQL state ownership or requiring Redis for local development.

## In scope

- Locked Dramatiq Redis dependency and validated `REDIS_URL` production configuration.
- Typed local/production queue selection at the application composition root.
- Production background submission that persists `queued` before publication and preserves that row on broker failure.
- Dedicated worker actor with `max_retries=0`, one-ID payload validation, lazy per-process application composition, and persisted duplicate-delivery gate.
- Redis/PostgreSQL conformance tests for payload, duplicate delivery, broker outage, and worker restart.

## Out of scope

Schema changes, job-attempt/lease creation, heartbeat, retry/backoff classification, durable cancellation, stale-running recovery, typed stage refactoring, artifact publication, production containers, and API contract changes.

## Existing code to reuse

- `JobStateStore` compare-before-write transitions from JOB-001.
- `IndexingService` current synchronous execution path and local background thread.
- `ProductionRepositoryStore.engine` and the application composition root.

## Implementation sequence

1. Add and lock Dramatiq 2.2.0 with the Redis extra.
2. Add queue port, validation, Dramatiq adapter, and stable publication failure.
3. Select the production adapter without connecting to Redis during local composition.
4. Persist production background jobs as queued, publish only their IDs, and add an existing-job execution entrypoint for the worker.
5. Add the duplicate-delivery gate and dedicated worker actor/command.
6. Verify Redis restart delivery and PostgreSQL exactly-once start behavior.

## Data/API compatibility and migration

No schema or HTTP shape changes. Local and synchronous indexing remain compatible. Production background responses may report `queued`; a broker failure leaves the durable queued row available for redispatch rather than deleting it.

## Failure, security, performance, and observability requirements

- Reject malformed job IDs before broker publication or worker database access.
- Use Dramatiq JSON encoding only; actor name, queue name, and argument count are fixed constants.
- Translate Redis errors into a stable message without including the Redis URL.
- Configure the indexing worker as one thread per process; broader concurrency requires capacity evidence.
- Duplicate/stale/terminal deliveries are acknowledged without a second execution. A crash after transition to `running` is intentionally unrecoverable until JOB-004 and must remain documented.

## Required tests and commands

```powershell
docker compose -f compose.integration.yml up -d postgres redis
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
$env:TEST_REDIS_URL='redis://127.0.0.1:56379/15'
backend\.venv\Scripts\python.exe -m pytest tests/jobs tests/persistence -q
backend\.venv\Scripts\python.exe -m pytest tests -q
backend\.venv\Scripts\uv.exe pip compile backend/requirements.txt --python-version 3.11 --universal --generate-hashes --output-file backend/requirements-lock.txt
git diff --exit-code -- backend/requirements-lock.txt
git diff --check
docker compose -f compose.integration.yml down
```

## Acceptance criteria

- Production settings reject a missing/invalid `REDIS_URL`; local settings start without Redis.
- The Dramatiq adapter produces a fixed actor/queue message containing exactly one string job ID and no kwargs.
- Broker outage raises the stable queue error and a previously persisted job remains `queued`.
- Two deliveries of one queued PostgreSQL job invoke the runner once; the second returns duplicate.
- An integration worker consumes an ID queued before startup and another ID after one stop/start cycle.
- Full backend regression and lock reproducibility pass.

## Rollback

Stop the worker, restore the local execution selection, remove Dramatiq/Redis configuration and the adapter/worker files, and regenerate the dependency lock. Queued PostgreSQL rows remain safe for a later dispatcher.

## Documentation and evidence updates

Complete this task, update source/test baselines and the worker runbook, record integration evidence, and advance project status to JOB-004.
