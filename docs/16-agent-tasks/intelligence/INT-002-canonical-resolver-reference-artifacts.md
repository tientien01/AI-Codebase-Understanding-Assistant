---
id: INT-002
title: Add canonical resolver and reference artifacts
status: completed
priority: P0
phase: 3
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [INT-001]
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
  - docs/16-agent-tasks/intelligence/INT-002-canonical-resolver-reference-artifacts.md
  - docs/18-production-evidence/resolution-accuracy-report.md
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
  - A versioned deterministic reference artifact retains every discovered Python import and call as resolved, ambiguous, or unresolved.
  - Resolved references contain exactly one same-repository target key, ambiguous references retain at least two sorted candidates, and unresolved references retain a stable reason with no target.
  - Reference identity, producer, method, support type, source span, repository/index ownership, and ordering are deterministic and JSON-serializable.
  - Static resolution uses only declared IR and repository symbol/file catalogs; no LLM, provider, database, graph traversal, or source reread is permitted.
  - Current compatibility graph output is projected from typed reference outcomes without changing API or persistence schemas.
evidence_outputs:
  - docs/18-production-evidence/resolution-accuracy-report.md
---

# Task INT-002 — Add canonical resolver and reference artifacts

## Context

The current CPG compatibility emitter performs call resolution while emitting graph edges. Its single-value symbol index overwrites duplicate names, external/unresolved classification is not represented as a typed artifact, and imports/calls are not retained uniformly as resolved, ambiguous, or unresolved outcomes.

## Objective

Create a deterministic Python resolver that consumes canonical IR plus declared repository catalogs, emits a strict versioned reference artifact for every import/call, and lets the compatibility emitter project those outcomes without owning resolution policy.

## In scope

- Strict reference artifact, outcome, span, producer, support and diagnostic/reason contracts.
- Deterministic raw import and call discovery from Python IR.
- Local qualified/bare function and class-method resolution, absolute/relative internal import resolution, alias-aware builtin/stdlib/framework/external classification, ambiguity retention and unresolved reasons.
- Stable ordering and canonical digest-safe serialization.
- Compatibility projection into existing graph nodes/edges and diagnostics.
- A synthetic `python_resolution_cases` accuracy matrix.

## Out of scope

Database persistence/migrations, non-Python resolver rules, inheritance/MRO, dynamic dispatch, framework endpoint-to-handler matching, graph-candidate schemas/normalization, capability thresholds, production worker composition, API/frontend changes, and full/incremental production equivalence.

## Existing code to reuse

- INT-001 `ParseRequest`, `IRModule`, `PythonAdapter`, and pipeline boundary.
- Current stable symbol/node ID helpers and CPG compatibility emitter.
- File inventory and already emitted repository symbol catalog; resolver inputs never reread source files.

## Implementation sequence

1. Define strict reference/outcome/span/artifact contracts and deterministic serialization.
2. Extract imports and call sites from IR with stable source ownership.
3. Resolve against declared module/symbol catalogs with explicit resolved, ambiguous and unresolved results.
4. Move compatibility call/import edge selection out of `CPGEmitter` and project typed outcomes.
5. Add the resolution matrix, run gates and publish evidence/baseline/status updates.

## Data/API compatibility and migration

No database migration or public API change. Typed reference artifacts are held in the current in-memory repository compatibility state; existing graph edge categories remain available. Persistence composition is deferred to an authorized pipeline/data task.

## Failure, security, performance, and observability requirements

- Inputs contain canonical relative paths/keys, IR facts and declared catalog entries only; no host paths or source payloads appear in diagnostics.
- Resolution and artifact bytes are stable under input ordering.
- Duplicate target names become explicit ambiguity; nothing silently wins by insertion order.
- Dynamic/attribute calls without deterministic ownership remain unresolved with stable reason codes.
- Resolver complexity is bounded by prebuilt indexes and output/reference counts; it performs no filesystem, network, provider or database access.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/intelligence/test_resolver_accuracy.py -q
backend\.venv\Scripts\python.exe -m pytest tests/intelligence tests/test_code_analysis.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The local profile is used. PostgreSQL/Redis-only tests may retain declared skips. Exact case counts, precision outcomes and limitations are recorded in `docs/18-production-evidence/resolution-accuracy-report.md`.

## Acceptance criteria

- Every fixture import/call yields exactly one typed reference outcome and stable canonical reference key.
- Local functions/class methods and internal absolute/relative imports resolve when exactly one target exists.
- Duplicate viable targets are ambiguous with sorted candidates; dynamic, missing and unsupported external targets are unresolved with stable reasons.
- Aliases classify builtin, stdlib, framework and external calls deterministically without claiming unavailable repository targets.
- Repeated and input-reordered resolution produces byte-equivalent artifact output.
- Existing call/import graph and code-analysis regressions pass from the typed compatibility projection.
- Targeted accuracy, intelligence regression, full backend and diff-hygiene commands pass.

## Rollback

Remove the unused resolver/artifact boundary and restore compatibility resolution inside `CPGEmitter`. No migration or persisted state rollback is required.

## Documentation and evidence updates

After every command passes, publish the resolution report, update fixture/source/test/capability baselines and project status, mark this task completed, and advance the next candidate to `INT-003` without claiming canonical graph validation.

## Closing evidence

- Python imports/calls now produce strict deterministic `resolved-reference-set/v1` artifacts before graph projection.
- The compatibility emitter consumes typed outcomes and no longer owns target-selection policy.
- The 5-test resolver gate, 34-test intelligence/code-analysis regression and 137-test local-profile backend suite passed.
- The reviewed matrix produced 9/9 exact outcomes; limitations are recorded in `docs/18-production-evidence/resolution-accuracy-report.md`.
