---
id: INT-006
title: Trace resolved Python values across direct function calls
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [INT-002, INT-003, UI-021]
requirements: []
contracts:
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
allowed_paths:
  - backend/app/services/code_analysis/models.py
  - backend/app/services/code_analysis/dfg/builder.py
  - backend/app/services/code_analysis/cpg/emitter.py
  - backend/app/services/code_analysis/pipeline.py
  - backend/app/services/graph/graph_schema_service.py
  - backend/app/services/graph/graph_projection_service.py
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - tests/test_code_analysis.py
  - tests/test_graph_projection.py
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/intelligence/INT-006-direct-interprocedural-value-trace.md
  - docs/18-production-evidence/direct-interprocedural-value-trace-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - frontend/package.json
  - frontend/package-lock.json
  - storage/**
dependency_changes:
  allowed: false
production_gates:
  - A statically resolved direct Python call binds supported caller arguments to callee parameters without matching by variable name alone.
  - A supported callee return binds back to the caller call result and its receiving definition.
  - Interprocedural expansion remains contextual, deterministic, provenance-labelled and bounded; unresolved or ambiguous calls remain explicit boundaries.
  - Existing intraprocedural Value Trace behavior and graph projection budgets remain compatible.
  - Focused backend/frontend tests, full frontend tests, lint, typecheck, build and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/direct-interprocedural-value-trace-report.md
---

# Task INT-006 — Direct Interprocedural Value Trace

## Context

The contextual Value Trace currently stops at function boundaries. The project owner authorized a bounded implementation task in the active conversation on 2026-07-16 after reviewing external evidence that developers primarily need producer, consumer, call-site and impact paths rather than a repository-wide variable catalogue.

## Objective

Extend the existing deterministic Python DFG compatibility path across statically resolved direct calls so a trace can cross caller arguments, callee parameters, supported returns and caller results without claiming runtime behavior.

## In scope

- Reuse stable parsed call/function identities and existing resolver outcomes to bind direct resolved Python calls.
- Emit typed inferred graph relations for supported argument-to-parameter and return-to-call-result steps.
- Preserve source locations, stable IDs, deterministic ordering and bounded progressive expansion.
- Present the new relation types in Value Trace with clear static-analysis language.
- Add positive, negative, ambiguous/unresolved and determinism regressions.

## Out of scope

- Regex-to-semantic-token replacement in Code Explorer.
- Dynamic dispatch, reflection, closures, generators, exceptions, mutation, alias or field-sensitive analysis.
- Cross-repository flow, taint/source/sink/sanitizer semantics or runtime traces.
- New dependencies, database schema, migrations or API fields.

## Existing code to reuse

- Universal Python IR and stable node identities under `backend/app/services/code_analysis`.
- Resolver-backed call/reference artifacts from `INT-002` and graph provenance normalization from `INT-003`.
- Contextual seed resolution and one-hop progressive expansion from `UI-021`.

## Implementation sequence

1. Confirm the current call/function IR identity and direct resolver boundary.
2. Add the smallest typed DFG representation needed for supported cross-function bindings.
3. Emit and project the new relations without broad graph fallback.
4. Add focused backend and frontend regressions and record evidence.

## Data/API compatibility and migration

No schema or API shape changes are allowed. New graph relation type values must remain compatible with the existing graph response vocabulary and old indexes remain readable without the new edges.

## Failure, security, performance, and observability requirements

- Never bind by name alone or invent a target for ambiguous/unresolved calls.
- Limit traversal through the existing depth/node/edge budgets and one-hop expansion contract.
- Label relations as inferred static support and retain evidence locations where available.
- Cycles and recursion must terminate deterministically.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/test_code_analysis.py tests/test_graph_projection.py -q
backend\.venv\Scripts\python.exe -m pytest tests/test_codebase_service.py -q
Set-Location frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- backend/app/services/code_analysis/models.py backend/app/services/code_analysis/dfg/builder.py backend/app/services/code_analysis/cpg/emitter.py backend/app/services/code_analysis/pipeline.py backend/app/services/graph/graph_schema_service.py backend/app/services/graph/graph_projection_service.py frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx tests/test_code_analysis.py tests/test_graph_projection.py docs/15-plans/task-register.md docs/16-agent-tasks/intelligence/INT-006-direct-interprocedural-value-trace.md docs/18-production-evidence/direct-interprocedural-value-trace-report.md
```

## Acceptance criteria

- A direct resolved call exposes a traceable caller-argument to callee-parameter path with source evidence.
- A supported returned value exposes a traceable callee-return to caller-result path.
- Ambiguous, unresolved and unsupported calls create no fabricated interprocedural value edge.
- Existing local DFG and contextual Value Trace tests remain green.
- Every declared verification command executes successfully before the task is marked complete.

## Rollback

Remove the new edge emission and UI labels; existing local DFG nodes, persisted indexes and API responses remain compatible.

## Documentation and evidence updates

Record exact behavior, limitations, commands and results in `docs/18-production-evidence/direct-interprocedural-value-trace-report.md`.

## Current verification state

Implemented and locally verified on 2026-07-16. The combined code-analysis and graph-projection suite passes 40 tests, the service integration suite passes 28 tests, the focused GraphPage suite passes 26 tests, and all 92 frontend tests, lint, TypeScript and the production build pass. Direct same-module resolved Python calls support bounded positional argument and return bindings; keyword, imported cross-file, dynamic, taint and runtime flow remain explicitly unsupported.
