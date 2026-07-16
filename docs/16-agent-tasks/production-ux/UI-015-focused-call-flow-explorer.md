---
id: UI-015
title: Deliver a focused evidence-backed Call Flow explorer
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-003, UI-010, UI-012, INT-003]
requirements: []
contracts:
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
decisions: []
technology_docs:
  - docs/03-technology/stack-overview.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/services/graph/graph_projection_service.py
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - tests/test_graph_projection.py
  - docs/16-agent-tasks/production-ux/UI-015-focused-call-flow-explorer.md
  - docs/18-production-evidence/focused-call-flow-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/app/services/parsing/**
  - backend/app/services/code_analysis/**
  - backend/app/services/indexing/**
  - backend/migrations/**
  - frontend/package.json
  - frontend/package-lock.json
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Call Flow begins with deterministic callable starting points rather than an unrelated repository-wide node slice.
  - A selected callable preserves complete caller-root and root-callee relations within bounded deterministic budgets.
  - Calls, Called by and Both are user-facing traversal modes with depth one by default and controlled one-hop expansion.
  - Default presentation collapses technical call-site hops when supported while retaining source/evidence metadata and explicit unresolved or external facts already present in the index.
  - Node and edge inspection exposes source, support, provenance, index and limitation evidence without presenting uncalibrated confidence as probability.
  - Fan-in, fan-out, recursion and cycle labels are projection-scoped signals, never global quality or dead-code claims.
  - Empty, limited and unsupported states state that missing static support does not prove missing runtime behavior.
  - Existing repository/index ownership, deterministic ordering, hard budgets, accessibility alternatives and no-dangling-edge invariants remain enforced.
  - Focused backend/frontend tests, typecheck, production build and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/focused-call-flow-report.md
---

# Task UI-015 — Focused Call Flow Explorer

## Context

The current Call Flow can request thousands of callable and call-site nodes before a root is selected. Generic node-first truncation can return a bounded canvas containing no complete call relation. The project owner authorized a complete Call Flow refinement in the active conversation on 2026-07-15.

## Objective

Turn Call Flow into a focused, progressively expandable static call-graph investigator centered on one callable, with inspectable source evidence and truthful analysis limits.

## In scope

- Deterministic callable starting points and root selection using stable indexed IDs.
- Calls, Called by and Both traversal, depth-one default and bounded progressive expansion.
- Caller–selected–callee presentation and relation-preserving budgets.
- Default suppression/collapse of technical call-site nodes where existing graph facts support it.
- Node and edge inspection with available source, support, provenance and index context.
- Existing resolved, external and unresolved call classifications when supplied by current graph facts.
- Projection-scoped direct fan-in/fan-out, recursion/cycle and limited-support signals.
- Honest empty/limited states, accessibility alternative and focused regression evidence.

## Out of scope

- Runtime tracing, profiling, execution order or branch certainty.
- Invented possible targets, call candidates, source expressions or calibrated probabilities absent from current indexed facts.
- New parser/resolver behavior, dependencies, persistence, migrations or graph producer changes.
- Global dead-code or code-quality conclusions.

## Required tests and commands

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest ..\tests\test_graph_projection.py -q
Set-Location ..\frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- backend/app/services/graph/graph_projection_service.py frontend/src/hooks/useAppController.ts frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx frontend/src/styles/pages/workspace.css frontend/src/types/api.ts tests/test_graph_projection.py docs/16-agent-tasks/production-ux/UI-015-focused-call-flow-explorer.md docs/18-production-evidence/focused-call-flow-report.md
```

## Acceptance criteria

- Opening Call Flow shows useful callable starting points and does not render an arbitrary 80-node/zero-edge slice.
- Selecting a callable presents bounded callers and callees with the selected root visually stable and direction labels understandable without graph jargon.
- A visible frontier can be expanded one hop without duplicate nodes/edges; focusing another callable intentionally resets the accumulated graph.
- Technical call sites do not dominate the default canvas; every shown semantic edge retains all evidence made available by the projection.
- Edge and node inspectors distinguish resolved/static support, external/unresolved facts, limited coverage and unknowns without treating confidence as a probability.
- Direct fan-in/fan-out and recursion/cycle signals declare their projection scope and do not label code as bad or unused.
- Keyboard users retain a complete relation-list alternative and all focused controls.

## Documentation and evidence updates

Record exact verification results and remaining parser/resolver limitations in `docs/18-production-evidence/focused-call-flow-report.md`. Do not mark this task completed until every declared local gate passes.

## Current verification state

Completed and locally verified on 2026-07-15. The focused backend projection suite passes 16 tests, the focused GraphPage suite passes 18 tests, all 77 frontend tests pass, ESLint and TypeScript pass, the Vite production build succeeds with 145 transformed modules, and declared diff hygiene passes. Runtime tracing, calibrated probability and unresolved multi-candidate resolution remain explicit non-claims.
