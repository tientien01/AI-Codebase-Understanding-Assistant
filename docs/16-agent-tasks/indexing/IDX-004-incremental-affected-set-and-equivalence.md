---
id: IDX-004
title: Add deterministic incremental planning and equivalence gates
status: completed
priority: P0
phase: 3
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [IDX-003]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/05-domain-contracts/indexing.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/05-domain-contracts/parsing/detailed-parser-output-schema.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/11-testing/specifications/detailed-testing-plan.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/services/indexing/incremental_planner.py
  - backend/app/services/indexing/equivalence_service.py
  - tests/indexing/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/indexing/IDX-004-incremental-affected-set-and-equivalence.md
  - docs/18-production-evidence/incremental-equivalence-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/migrations/**
  - backend/app/db/**
  - backend/app/api/**
  - backend/app/services/indexing/indexing_service.py
  - backend/app/services/indexing/phase_pipeline.py
  - backend/app/services/indexing/job_state_store.py
  - backend/app/services/parsing/**
  - backend/app/services/code_analysis/**
  - backend/app/services/graph/**
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
  - Snapshot entries, component compatibility, dependency edges, change classifications, affected-set budgets, reuse decisions, and equivalence outputs are strict immutable typed contracts.
  - Added, deleted, content, documentation, structure, public-API, dependency, exact move, and ambiguous move candidates are classified deterministically without line-number identity.
  - Reuse is allowed only when content, producer, schema, rules, security policy, and normalized configuration identities are compatible.
  - Affected-set expansion follows only declared typed reverse dependencies and is bounded by node, depth, and repository-fraction limits.
  - Any incompatible component, unknown dependency endpoint/type, ambiguous unsafe reuse, or exceeded budget deterministically falls back to a full build with stable reason codes.
  - Full and incremental target snapshots compare exact canonical facts, references, graph, chunks, readiness, fingerprints, and benchmark-answer identities; mismatches fail with bounded deterministic diagnostics.
evidence_outputs:
  - docs/18-production-evidence/incremental-equivalence-report.md
---

# Task IDX-004 — Add deterministic incremental planning and equivalence gates

## Context

The durable indexing foundation can publish and activate immutable versions, but production code lacks a typed incremental affected-set planner and an executable equivalence gate. Existing MVP incremental behavior is not sufficient evidence because it does not encode component compatibility, typed dependency expansion, fallback reasons, or canonical output comparison.

## Objective

Add a deterministic planner that either produces a bounded safe incremental rebuild/reuse plan or explicitly falls back to full, plus an exact canonical equivalence comparator for full and incremental target outputs.

## In scope

- Strict snapshot file fingerprints covering raw content, normalized/structure/public-API/dependency/documentation identities and producer/configuration compatibility.
- Deterministic added/deleted/change classification and exact unique-content move candidates.
- Typed dependency edges and bounded reverse affected-set expansion.
- Stable full-fallback reason codes for component incompatibility, invalid dependency graphs, ambiguity, and budget limits.
- Explicit rebuild, reuse, delete, and move-candidate plan output.
- Strict canonical equivalence snapshots and bounded mismatch diagnostics across mandatory output families.
- Synthetic fixture matrix covering add, edit, delete, move, rename/signature/public API, dependency, component-version, ambiguous move, and budget fallback cases.

## Out of scope

Changing the current local indexer, parser consolidation, language adapters, resolver rules, graph normalization, production worker wiring, database schema/state, artifact cleanup, API/frontend behavior, and defining numeric production capacity thresholds without benchmark evidence.

## Existing code to reuse

- Stable canonical identity and versioned artifact contracts.
- IDX-002 typed phase/configuration identity boundary.
- IDX-003 validated immutable activation boundary.
- Existing deterministic parser/graph behavior remains baseline input only and is not modified by this task.

## Implementation sequence

1. Define strict file/component/dependency/change/plan contracts.
2. Classify file changes and exact unique move candidates without mutating canonical identity.
3. Validate component compatibility and dependency ownership/types.
4. Expand affected files through bounded typed reverse dependencies and emit stable full-fallback reasons.
5. Define canonical full/incremental equivalence snapshots and bounded exact diagnostics.
6. Add the fixture matrix and update evidence/baseline/status documents.

## Data/API compatibility and migration

No migration, persisted format, API, or current indexing behavior changes. These are new internal planning/equivalence boundaries for later composition with the typed production pipeline.

## Failure, security, performance, and observability requirements

- Inputs contain relative POSIX paths, canonical keys, lowercase SHA-256 identities, and no host paths or source contents.
- The planner never reads repositories, artifacts, databases, or providers; every fact and edge is declared.
- Expansion order and diagnostics are stable under input ordering.
- Limits are positive typed inputs. This task tests enforcement mechanics with synthetic values and does not claim universal production thresholds.
- Unknown relationship types/endpoints, duplicate keys/paths, incompatible component identities, or unsafe ambiguity never silently reuse prior outputs.
- Equivalence diagnostics disclose canonical family/key and digests only, not source payloads.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/indexing/test_incremental_planner.py tests/indexing/test_equivalence_service.py -q
backend\.venv\Scripts\python.exe -m pytest tests/indexing -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

Tests use deterministic synthetic metadata only. Exact results and the fixture/change matrix are recorded in `docs/18-production-evidence/incremental-equivalence-report.md`.

## Acceptance criteria

- Stable input order produces byte-equivalent plan output and stable reason ordering.
- Add, delete, content, documentation-only, structure, public-API, dependency, exact move, and ambiguous-move cases produce the declared classifications.
- Compatible unchanged files are reusable; incompatible producer/schema/rule/security/configuration identities force full rebuild.
- Reverse dependency expansion rebuilds affected dependents within limits and falls back to full on invalid edges or any node/depth/fraction limit.
- The plan never marks deleted, changed, affected, ambiguous, or incompatible files reusable.
- Equivalent full/incremental canonical snapshots pass; a mismatch in every mandatory family fails with stable bounded diagnostics.
- Targeted planner/equivalence tests, indexing regression, full backend regression, and diff hygiene pass.

## Rollback

Remove the unused internal planner/equivalence modules and their tests/docs. No runtime composition, database, API, or active index changes in this task.

## Documentation and evidence updates

Complete only after every command passes. Update source/test baselines and project status, publish the equivalence report, and advance the next candidate to `INT-001` without claiming parser/resolver/graph consolidation or production-worker composition.

## Closing evidence

- Implemented the strict immutable planner and canonical equivalence contracts within the allowed paths.
- Verified the complete synthetic change, fallback, dependency-expansion, and mandatory-family comparison matrix.
- Published exact local-profile results and scope limitations in `docs/18-production-evidence/incremental-equivalence-report.md`.
- No runtime indexer, parser, graph, worker, database, API, dependency, or frontend behavior changed.
