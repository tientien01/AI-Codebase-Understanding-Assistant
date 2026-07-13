---
id: IDX-003
title: Validate candidate indexes and activate atomically
status: completed
priority: P0
phase: 2
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [IDX-002, JOB-004]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/04-domain-and-data/specifications/detailed-data-model.md
  - docs/04-domain-and-data/specifications/detailed-storage-design.md
  - docs/05-domain-contracts/indexing.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/environment-and-configuration.md
  - docs/11-testing/specifications/detailed-testing-plan.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/services/indexing/validation_service.py
  - backend/app/services/indexing/activation_service.py
  - backend/app/services/indexing/job_state_store.py
  - backend/app/services/artifacts/**
  - tests/indexing/**
  - tests/jobs/test_job_state_store.py
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/indexing/IDX-003-validation-and-atomic-activation.md
  - docs/18-production-evidence/validation-atomic-activation-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/migrations/**
  - backend/app/db/production_models/**
  - backend/app/db/models.py
  - backend/app/api/**
  - backend/app/services/indexing/indexing_service.py
  - backend/app/services/indexing/job_delivery_service.py
  - backend/app/services/indexing/phase_pipeline.py
  - backend/app/workers/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Candidate validation is deterministic, typed, and blocks activation for schema/checksum/ownership failures, missing mandatory artifacts, critical issues, or non-ready mandatory capabilities.
  - Optional capability failure is recorded without blocking otherwise valid mandatory capabilities.
  - Manifest publication completes before activation and only checksum-verified immutable artifacts are accepted.
  - Activation runs in one PostgreSQL transaction that locks the repository, job, attempt, candidate, and expected previous active version.
  - Activation rechecks lease generation, operation generation, running attempt, unexpired lease, cancellation, candidate readiness, registered artifact metadata, validation, capability readiness, and expected previous active version.
  - Success marks the candidate active, the previous version superseded, the job/attempt succeeded, updates the repository pointer, and writes an audit event atomically.
  - Any failed predicate or injected transaction failure preserves the prior active version and prevents partial success; cancellation after committed activation is too late.
evidence_outputs:
  - docs/18-production-evidence/validation-atomic-activation-report.md
---

# Task IDX-003 — Validate candidate indexes and activate atomically

## Context

IDX-001 and IDX-002 provide immutable artifacts, terminal manifests, typed phases, and validated checkpoint resume. PostgreSQL already contains repository, job, attempt, version, artifact, validation, capability, and audit tables, but runtime code has no typed activation validator or one-transaction expected-previous-version switch.

## Objective

Add deterministic candidate validation and a fenced PostgreSQL activation boundary that either commits the complete active-version transition or preserves the previous active version unchanged.

## In scope

- Strict validation issue, capability readiness, candidate validation, and activation request/result contracts.
- Deterministic checks for manifest status/schema/ownership, artifact checksum metadata, mandatory artifact presence, critical issues, and mandatory capability readiness.
- Optional capability degradation without unrelated activation failure.
- Immutable terminal manifest publication before the database transaction.
- PostgreSQL persistence of validation issues and capability readiness.
- Atomic activation with row locks, expected previous pointer, job/attempt/lease/operation fencing, cancellation check, artifact metadata comparison, lifecycle transitions, repository pointer update, and audit event.
- Integration tests for success, cancellation, lease/generation conflicts, missing/corrupt artifacts, validation failure, expected-active conflict, rollback, and failed-build preservation.

## Out of scope

Database migrations, concrete parser/graph validation algorithms, production worker wiring, local indexing rewrite, incremental planning/equivalence, cleanup/retention, API/frontend behavior, backup/restore, and deployment changes.

## Existing code to reuse

- IDX-001 typed manifest, immutable artifact store, publisher, and checksum verification.
- IDX-002 typed phase outputs and checkpoint boundary.
- JOB-004 persisted attempt leases, generation fencing, durable cancellation, and terminal transitions.
- Existing PostgreSQL `validation_issues`, `capability_readiness`, `audit_events`, repository/version/artifact/job/attempt models and constraints.

## Implementation sequence

1. Define typed validation/capability/activation contracts with strict ownership and stable enums.
2. Validate the manifest, declared/mandatory artifacts, issues, and capability readiness deterministically.
3. Publish the terminal immutable manifest only after validation passes.
4. Add the fenced atomic activation command to the PostgreSQL job-state boundary.
5. Compose validation, publication, and activation behind one internal service without changing current worker behavior.
6. Add targeted and PostgreSQL integration tests, then record evidence/baseline/status updates.

## Data/API compatibility and migration

No migration or API change is allowed. The existing production schema is authoritative. New service models are internal and versioned where serialized. SQLite/local behavior remains unchanged.

## Failure, security, performance, and observability requirements

- Validation uses only typed declared facts and immutable artifact metadata; it does not infer readiness with LLM output or hidden thresholds.
- Every stored artifact used for activation is checksum/size verified and repository/version owned.
- Error messages expose opaque logical IDs and stable failure classes, never storage roots, database URLs, payloads, or secrets.
- Activation uses bounded row reads/updates in one transaction and performs no large artifact reads while locks are held.
- A stale lease, stale operation generation, cancellation, unexpected active version, invalid lifecycle, missing metadata, or failed readiness aborts before pointer mutation.
- Transaction rollback preserves the old active version, candidate inactivity, job/attempt non-success, and absence of a success audit.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/indexing -q
docker compose -f compose.integration.yml up -d postgres redis
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
$env:TEST_REDIS_URL='redis://127.0.0.1:56379/15'
backend\.venv\Scripts\python.exe -m pytest tests/jobs/test_job_state_store.py tests/indexing -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
docker compose -f compose.integration.yml down
```

Filesystem validation uses synthetic `tmp_path` artifacts. PostgreSQL/Redis use the disposable pinned integration profile. Exact results are recorded in `docs/18-production-evidence/validation-atomic-activation-report.md`.

## Acceptance criteria

- Typed validation rejects foreign ownership, malformed checksums, duplicate declarations, missing mandatory artifacts, critical issues, and failed/unavailable mandatory capabilities.
- Optional failed capabilities remain recorded and do not block a valid mandatory set.
- Missing/corrupt storage objects prevent manifest publication and activation.
- A valid candidate atomically becomes active, the expected prior active version becomes superseded, the repository pointer changes, job/attempt succeed, and one activation audit is written.
- Cancellation, stale lease/generation, unexpected prior active version, invalid candidate lifecycle, or registered-artifact mismatch produces no partial activation.
- An injected exception after database updates rolls back every activation effect and preserves the prior active version.
- Targeted validation, PostgreSQL activation integration, full regression, and diff hygiene gates pass.

## Rollback

Remove the new validator/activation service and atomic store command. No migration, API, worker wiring, or active production data is introduced by this task branch.

## Documentation and evidence updates

Complete only after every declared command passes. Update source/test baselines and project status, publish the atomic activation report, and advance the next candidate to `IDX-004` without claiming incremental equivalence or release readiness.

## Closing evidence

Completed on 2026-07-13. The local indexing gate passed 15 tests with 5 PostgreSQL cases skipped, the integration job-state/indexing gate passed 24 tests, and the full pinned-profile backend regression passed 132 tests. Exact commands, transaction invariants, results, and remaining scope are recorded in `docs/18-production-evidence/validation-atomic-activation-report.md`.
