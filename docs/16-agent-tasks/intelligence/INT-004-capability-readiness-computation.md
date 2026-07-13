---
id: INT-004
title: Compute capability readiness from validated evidence
status: completed
priority: P0
phase: 3
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [INT-003]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/04-domain-and-data/specifications/detailed-data-model.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
  - docs/05-domain-contracts/parsing-and-graph.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/11-testing/specifications/detailed-testing-plan.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/services/code_analysis/capability_readiness.py
  - tests/intelligence/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-3-code-intelligence.md
  - docs/15-plans/phases/phase-4-retrieval-and-evidence.md
  - docs/16-agent-tasks/intelligence/INT-004-capability-readiness-computation.md
  - docs/18-production-evidence/capability-readiness-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/**
  - backend/app/db/**
  - backend/app/services/graph/**
  - backend/app/services/indexing/**
  - backend/app/services/parsing/**
  - backend/app/services/repositories/**
  - backend/app/workers/**
  - backend/migrations/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Readiness output uses only ready, limited, unavailable, failed, or stale and is deterministic under input order.
  - Required artifact missing/failed/stale, critical validation, unsupported/no-input profiles, partial coverage, unresolved references, dependencies and optional providers map to stable reason codes without hidden numeric thresholds.
  - One failed file yields measured limited coverage while complete profile failure yields failed; unresolved count alone never blocks an otherwise activatable mandatory capability.
  - Optional capability/provider failure never changes unrelated mandatory core capability state.
  - Mandatory activation summary permits only ready or limited and rejects failed, unavailable, or stale mandatory capabilities.
  - Output reuses the accepted CapabilityReadiness schema and produces manifest-compatible state summaries.
evidence_outputs:
  - docs/18-production-evidence/capability-readiness-report.md
---

# Task INT-004 — Compute capability readiness from validated evidence

## Context

`CapabilityReadiness` and activation validation exist, but callers must currently construct readiness records manually. There is no deterministic calculator connecting validated artifacts, profile coverage, unresolved references, graph issues, source freshness, optional providers and capability dependencies to the accepted readiness states.

## Objective

Add a strict deterministic calculator that consumes declared validated evidence, emits manifest-compatible readiness records and a mandatory activation summary, and proves the Phase 3 readiness invariants without claiming release readiness.

## In scope

- Immutable capability specification, evidence and report contracts.
- Required artifact, supported-profile, measured coverage, unresolved-reference, critical-validation, freshness, provider and dependency rules.
- Stable reason codes, coverage payloads, remediation and validation issue linkage.
- Deterministic dependency evaluation, input-order independence and cycle/unknown-dependency rejection.
- Mandatory capability activation summary and manifest state projection.
- Readiness invariant matrix covering ready, limited, unavailable, failed and stale.

## Out of scope

Manifest publication/activation changes, database persistence, API/frontend exposure, capability threshold benchmarking, non-declared source inspection, provider calls, production worker composition, release readiness, and retrieval implementation.

## Existing code to reuse

- Accepted `CapabilityReadiness` schema and `CandidateValidator` activation state rules.
- INT-001 through INT-003 evidence facts and stable validation issue semantics.
- Accepted indexing failure/optional-provider behavior and readiness state contract.

## Implementation sequence

1. Define strict capability spec/evidence/report inputs and validate ownership/set/dependency invariants.
2. Compute artifact, validation, freshness, support, coverage, unresolved and provider base states.
3. Apply dependency states deterministically and emit stable readiness/remediation/coverage.
4. Compute mandatory activation and manifest-compatible summaries.
5. Add invariant matrix, run gates and publish evidence/baseline/phase/status updates.

## Data/API compatibility and migration

No migration or public API change. The calculator returns the existing readiness schema for later manifest/activation composition; it does not persist or activate a candidate.

## Failure, security, performance, and observability requirements

- Inputs are declared counts, states, artifact names and issue IDs only; no source content, host path, filesystem/database/provider/network access.
- Counts are non-negative and successful/unresolved counts cannot exceed declared totals.
- Unknown/duplicate/cyclic dependencies and mismatched spec/evidence sets fail closed before calculation.
- Reason and capability ordering is stable; coverage exposes measured counts/fraction and never implies an undocumented pass percentage.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/intelligence/test_capability_readiness.py -q
backend\.venv\Scripts\python.exe -m pytest tests/intelligence tests/indexing/test_validation_activation.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The local profile is used. PostgreSQL/Redis-only tests may retain declared skips. Exact invariant results and limitations are recorded in `docs/18-production-evidence/capability-readiness-report.md`.

## Acceptance criteria

- The fixture matrix produces every accepted readiness state and the expected stable reason/coverage output.
- Partial parser coverage and unresolved references produce limited, not failed; complete parser failure produces failed.
- Missing/failed artifacts, critical issues, stale source, unsupported/no-input profile and optional provider cases remain capability-scoped.
- Dependency limited propagates limited; dependency failed/unavailable prevents dependent readiness; cycles/unknown dependencies reject input.
- Mandatory activation is true only when every mandatory capability is ready or limited.
- Reordered specs/evidence/artifacts/reasons produce byte-equivalent report output.
- Targeted readiness, intelligence/activation regression, full backend and diff-hygiene gates pass.

## Rollback

Remove the unused calculator/tests/docs. No migration, persisted state or runtime activation rollback is required.

## Documentation and evidence updates

After every command passes, publish the readiness report, update source/test/capability baselines, mark Phase 3 exit evidence without claiming production equivalence, unblock Phase 4 planning, mark this task completed, and advance the next candidate to `RET-001`.

## Closing evidence

- Declared validated evidence now maps deterministically into the accepted five readiness states and manifest-compatible summaries.
- Partial/unresolved mandatory capabilities remain activatable as limited; fatal/unavailable/stale mandatory states block the summary.
- The 11-test readiness gate, 37-pass/5-skip intelligence/activation regression and 152-pass local-profile backend suite completed successfully.
- Exact invariants and production-composition limitations are recorded in `docs/18-production-evidence/capability-readiness-report.md`.
