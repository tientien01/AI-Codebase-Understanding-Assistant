---
id: JOB-001
title: Persist the job, version, and artifact state machine
status: completed
priority: P0
phase: 2
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [DAT-003]
requirements: []
contracts:
  - docs/04-domain-and-data/postgresql-physical-schema.md
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/04-domain-and-data/specifications/detailed-data-model.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/stack-overview.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/services/indexing/job_state_store.py
  - tests/jobs/**
  - .github/workflows/ci.yml
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/indexing/JOB-001-persisted-job-version-artifact-state.md
  - docs/18-production-evidence/job-state-transition-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/migrations/**
  - backend/app/db/models.py
  - backend/app/db/session.py
  - backend/app/api/**
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Job, version, and artifact transitions use PostgreSQL transactions and reject invalid prior states.
  - Concurrent active-job and version ownership constraints remain enforced by the DAT-002 schema.
  - Artifact identity, checksum, size, producer, retention, and finalization fields are immutable after insertion.
  - Lease claim, heartbeat, retry, queue delivery, and activation remain outside JOB-001.
evidence_outputs:
  - docs/18-production-evidence/job-state-transition-report.md
---

# Task JOB-001 — Persist the job, version, and artifact state machine

## Objective

Provide the transactional PostgreSQL command boundary for creating and transitioning index jobs, candidate versions, and immutable artifact records before queue/lease behavior is introduced.

## In scope

- Transactional job plus candidate-version submission.
- Explicit validated job and version transitions with compare-before-write semantics.
- Immutable artifact registration bound to repository/version.
- Ownership, duplicate active job, invalid transition, rollback, and idempotent terminal-read tests.

## Out of scope

Queue selection/delivery, attempts, leases, heartbeat, retry/recovery, stage execution, manifest publication, validation/readiness, and atomic activation.

## Required tests and commands

```powershell
docker compose -f compose.integration.yml up -d postgres
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
backend\.venv\Scripts\python.exe -m pytest tests/jobs -q
backend\.venv\Scripts\python.exe -m pytest tests/persistence tests/migrations -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
docker compose -f compose.integration.yml down
```

## Acceptance criteria

- Submission creates one queued job and one building target version atomically.
- Only declared state edges succeed; stale expected states update zero rows and raise a stable conflict.
- Artifact registration validates checksum/size/count and cannot overwrite an existing artifact.
- Cross-repository version/artifact ownership fails without partial writes.

## Rollback

Revert JOB-001 code/tests; no schema downgrade is required.
