---
id: INT-003
title: Enforce graph candidate provenance and normalization
status: completed
priority: P0
phase: 3
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [INT-002]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/05-domain-contracts/parsing/detailed-parser-output-schema.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/11-testing/fixture-catalog.md
  - docs/11-testing/specifications/detailed-testing-plan.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/services/code_analysis/**
  - backend/app/services/index_models.py
  - tests/intelligence/**
  - tests/test_code_analysis.py
  - docs/11-testing/fixture-catalog.md
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/16-agent-tasks/intelligence/INT-003-graph-candidate-provenance-normalization.md
  - docs/18-production-evidence/graph-validation-report.md
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
  - Reference-derived graph nodes and edges are strict versioned candidates with canonical keys, repository/index ownership, origin, producer, support type and source provenance.
  - Normalization retains accepted, changed and dropped candidate audit state and emits stable bounded issue codes/severities.
  - Only one canonical edge direction is accepted; inverse aliases are deterministically reversed and marked changed rather than stored as duplicates.
  - Dangling endpoints, conflicting canonical keys, invalid candidate shape/type/provenance and invalid inferred confidence are critical and excluded from active output.
  - Exact duplicates merge deterministically; input ordering does not affect normalized artifact bytes.
  - Current reference compatibility edges are projected only from candidates that pass normalization with zero critical issues.
evidence_outputs:
  - docs/18-production-evidence/graph-validation-report.md
---

# Task INT-003 — Enforce graph candidate provenance and normalization

## Context

The legacy graph schema service normalizes mutable DTOs after emission, drops dangling edges with warnings, and does not retain a typed candidate audit trail. INT-002 provides canonical reference outcomes, but resolved references are still projected directly into compatibility graph edges without a candidate provenance/validation gate.

## Objective

Build strict provenance-bearing node/edge candidates from resolved references, deterministically normalize and validate them, retain changed/dropped audit state and issues, and permit compatibility projection only from zero-critical accepted output.

## In scope

- Strict graph-candidate, normalization-issue and normalized-graph artifact contracts.
- Reference-derived file/symbol node candidates and canonical `imports`/`calls` edge candidates.
- Canonical direction mapping, exact duplicate merge, deterministic ordering and bounded diagnostics.
- Validation for shape, allowed type/relation/origin/support, ownership, spans, endpoints, conflicting keys and explicit inferred-confidence policy.
- In-memory candidate/report retention and a compatibility projection gate.
- Synthetic invalid-candidate matrix and zero-critical valid pipeline fixture.

## Out of scope

Database persistence/migrations, graph query/projection APIs, legacy `GraphSchemaService` replacement, CFG/DFG candidate conversion, non-Python producers, cross-file resolver expansion, capability readiness thresholds, production worker composition, frontend behavior and full/incremental production equivalence.

## Existing code to reuse

- INT-001 canonical keys/spans and INT-002 reference artifacts.
- Current compatibility emitter and stable DTO projection behavior.
- Accepted graph direction/origin/support contracts and existing graph regressions.

## Implementation sequence

1. Define immutable candidate, issue, policy and normalized artifact contracts.
2. Build file/symbol nodes plus `imports`/`calls` edge candidates from resolved references.
3. Normalize direction/deduplicate and validate ownership, provenance, endpoints, types and policy.
4. Retain audit/report state and gate compatibility projection on accepted zero-critical output.
5. Add invalid/valid matrices, run gates and publish evidence/baseline/status updates.

## Data/API compatibility and migration

No database migration or public API change. Candidate/report state is an internal in-memory boundary. Existing graph DTO categories remain compatibility output; database composition and legacy graph service replacement require later authorized work.

## Failure, security, performance, and observability requirements

- Candidates contain canonical keys, digest-safe metadata and provenance only; no source payload or host path.
- Critical invalid candidates never reach active output; prior compatibility behavior remains available for unresolved/inferred local views but cannot be claimed as canonical confirmed graph.
- Inferred-confidence minimum is an explicit typed policy input used only by synthetic enforcement tests; no universal production threshold is claimed.
- Normalization uses bounded sorted indexes and bounded issue messages, with no filesystem/network/database/provider/LLM access.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/intelligence/test_graph_candidates.py -q
backend\.venv\Scripts\python.exe -m pytest tests/intelligence tests/test_code_analysis.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The local profile is used. PostgreSQL/Redis-only tests may retain declared skips. Exact matrix/results and limitations are recorded in `docs/18-production-evidence/graph-validation-report.md`.

## Acceptance criteria

- Valid resolved import/call references produce canonical node/edge candidates with complete ownership, origin, producer, support and span provenance.
- Valid fixture normalization reports zero critical issues and compatibility call/import regressions pass.
- Inverse edge aliases are reversed once and marked changed; exact duplicates are deterministic; no inverse duplicate reaches active output.
- Dangling, conflicting, invalid type/relation/shape/provenance and below-policy inferred candidates are dropped with stable expected issue codes; critical count matches the fixture.
- Reordered candidate input produces byte-equivalent normalized output.
- Targeted graph, intelligence/code-analysis, full backend and diff-hygiene gates pass.

## Rollback

Remove the unused candidate/report boundary and restore direct reference compatibility projection. No migration or persisted state rollback is required.

## Documentation and evidence updates

After every command passes, publish graph validation evidence, update fixture/source/test/capability baselines and project status, mark this task completed, and advance the next candidate to `INT-004` without claiming capability readiness.

## Closing evidence

- Resolved Python reference edges now pass strict candidate provenance and deterministic normalization/audit contracts.
- Zero-critical active output gates resolved compatibility projection; invalid candidates never become active.
- The 4-test graph gate, 38-test intelligence/code-analysis regression and 141-test local-profile backend suite passed.
- The valid fixture has zero critical issues; the invalid matrix reports the expected seven failure families and eight critical issues in `docs/18-production-evidence/graph-validation-report.md`.
