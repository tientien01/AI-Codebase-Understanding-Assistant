---
id: IDX-002
title: Add typed indexing phases and validated checkpoint resume
status: completed
priority: P0
phase: 2
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [IDX-001, JOB-003]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
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
  - backend/app/services/indexing/phase_contracts.py
  - backend/app/services/indexing/phase_pipeline.py
  - backend/app/services/artifacts/**
  - tests/indexing/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/indexing/IDX-002-typed-indexing-phases-and-checkpoints.md
  - docs/18-production-evidence/indexing-phase-checkpoint-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/migrations/**
  - backend/app/db/**
  - backend/app/api/**
  - backend/app/services/indexing/indexing_service.py
  - backend/app/services/indexing/job_state_store.py
  - backend/app/services/indexing/job_delivery_service.py
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
  - Every phase has typed immutable input/output, stable phase and schema versions, a bounded resource policy, an idempotency key, and an explicit cancellation boundary.
  - The pipeline accepts only the canonical ordered phase set and never infers inputs by rescanning storage.
  - A completed phase checkpoint is an immutable checksum-verified artifact scoped to one repository and index version.
  - Resume skips only the longest valid completed prefix; a missing, corrupt, incompatible, or out-of-order checkpoint restarts from that phase.
  - A phase output is published as a checkpoint only after execution succeeds and cancellation has been checked; partial failures are never resumable checkpoints.
  - Duplicate execution with identical identity and bytes is idempotent; conflicting checkpoint bytes fail without overwriting the first result.
evidence_outputs:
  - docs/18-production-evidence/indexing-phase-checkpoint-report.md
---

# Task IDX-002 — Add typed indexing phases and validated checkpoint resume

## Context

IDX-001 provides immutable checksum-verified artifact storage, but indexing still lacks an executable typed phase boundary and a deterministic rule for resuming from validated completed-stage artifacts. Queue delivery and lease recovery exist, while production activation remains reserved for IDX-003.

## Objective

Add a typed phase contract and storage-backed phase runner that publishes immutable checkpoint envelopes and resumes only from the longest compatible checksum-verified prefix.

## In scope

- Canonical production-v1 phase identifiers and ordering.
- Strict immutable phase input/output, resource-policy, execution-context, and checkpoint-envelope models.
- Deterministic phase idempotency keys derived from repository/version, phase version, input artifact identity, and configuration identity.
- A registry-validated phase pipeline that uses declared inputs only.
- Checkpoint serialization, immutable artifact publication, checksum verification, and prefix-only resume planning.
- Cancellation checks before execution and before checkpoint publication.
- Unit tests for ordering, typing, idempotency, corruption, incompatibility, cancellation, failure, and resume behavior.

## Out of scope

Rewriting the legacy local indexing implementation, production worker wiring, database migrations, lease predicates, PostgreSQL artifact-row registration, validation issue calculation, manifest finalization, activation, incremental affected-set logic, cleanup/retention, API changes, and frontend changes.

## Existing code to reuse

- IDX-001 `ArtifactStorePort`, safe artifact keys, immutable filesystem adapter, and stable integrity/conflict errors.
- Existing persisted jobs, attempts, leases, and artifact metadata; this task does not alter their schema or transitions.
- Pydantic and Python standard-library hashing/JSON facilities already locked by the repository.

## Implementation sequence

1. Define strict phase identities, resource bounds, declared artifact references, execution context, and output/checkpoint schemas.
2. Validate the canonical ordered registry and deterministic idempotency derivation.
3. Add checkpoint logical keys and deterministic checkpoint envelope bytes.
4. Implement prefix-only checkpoint discovery with exact checksum and compatibility validation.
5. Implement execution, cancellation boundaries, immutable checkpoint publication, and stable phase failures.
6. Add targeted tests and update evidence/baseline/status documents.

## Data/API compatibility and migration

No database or API migration is allowed. The runner is a new internal application boundary for later production-worker composition. Checkpoint payloads use versioned schemas and repository/index-version-owned artifact keys; existing local indexing behavior is unchanged.

## Failure, security, performance, and observability requirements

- Phase code receives only its typed declared input and context; the runner does not scan repositories or storage for undeclared data.
- Resource limits are positive, finite integers and are part of phase identity.
- Cancellation is checked before phase execution and immediately before immutable publication.
- Exceptions and invalid outputs never create a completed checkpoint.
- Resume validates envelope schema, repository/version/phase ownership, phase version, input/configuration hashes, payload checksum/size, and contiguous canonical order.
- Missing or invalid checkpoints stop prefix discovery at that phase; later artifacts cannot cause unsafe skipping.
- Errors expose logical identities only and never host paths or checkpoint payload content.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/indexing -q
backend\.venv\Scripts\python.exe -m pytest tests/artifacts -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

Tests use only `tmp_path`, deterministic synthetic bytes, and in-process phase doubles. Exact results are recorded in `docs/18-production-evidence/indexing-phase-checkpoint-report.md`.

## Acceptance criteria

- Invalid phase order, duplicate phase IDs, unbounded policies, malformed identities, and undeclared output metadata fail before execution.
- Equal phase identity produces the same idempotency key; any version/input/configuration change produces a different key.
- Successful phases publish deterministic immutable checkpoint envelopes at canonical keys.
- Failures or cancellation before publication leave no checkpoint for that phase.
- Resume skips a contiguous compatible prefix and stops at the first missing, corrupt, incompatible, or invalid checkpoint even when later checkpoints exist.
- Identical retry is idempotent and conflicting immutable checkpoint bytes preserve the first object.
- Targeted phase tests, artifact regression, full backend regression, and diff hygiene pass.

## Rollback

Remove the new unused internal phase contract/runner and checkpoint helpers. No current worker, API, database state, or active index changes in this task.

## Documentation and evidence updates

Complete only after every declared command passes. Update source/test baselines and project status, publish the checkpoint report, and advance the next candidate to `IDX-003` without claiming validation, activation, or Phase 2 completion.

## Closing evidence

Completed on 2026-07-13. The targeted indexing suite passed 9 tests, artifact regression passed 18 tests, and the declared local-profile backend regression passed 97 tests with 24 production integration tests skipped. Exact commands, results, invariants, and scope boundaries are recorded in `docs/18-production-evidence/indexing-phase-checkpoint-report.md`.
