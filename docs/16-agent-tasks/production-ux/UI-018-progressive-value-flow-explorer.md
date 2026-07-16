---
id: UI-018
title: Deliver a focused progressive Value Flow explorer
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-003, UI-010, UI-015, UI-017, INT-003]
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
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/production-ux/UI-018-progressive-value-flow-explorer.md
  - docs/18-production-evidence/progressive-value-flow-report.md
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
  - Value Flow starts from deterministic indexed value candidates rather than an unrelated repository-wide DFG slice.
  - Comes from, Flows to and Both are user-facing traversal modes backed by bounded incoming, outgoing and bidirectional graph traversal.
  - Expansion adds one supported hop at a time, retains stable indexed IDs and never invents missing transformations or cross-function relations.
  - Parameter, definition and use roles are presented semantically while stored DFG node and edge truth remains unchanged.
  - Value and relation inspectors expose available source, role, support, provenance, scope and limitation evidence.
  - Empty, partial and unsupported states state that absent static support does not prove absent runtime behavior.
  - Existing repository/index ownership, deterministic ordering, hard budgets, accessibility alternatives, direct canvas manipulation and no-dangling-edge invariants remain enforced.
  - Focused backend/frontend tests, lint, typecheck, production build and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/progressive-value-flow-report.md
---

# Task UI-018 — Progressive Value Flow Explorer

## Context

Value Flow currently uses the generic graph page and requests a broad DFG projection before a value is selected. The current analyzer emits stable intraprocedural parameter, definition and use nodes with inferred DFG relations, but it does not prove call-result nodes, independent return nodes, transformations, mutation, interprocedural binding or taint semantics. The project owner authorized this task in the active conversation on 2026-07-15.

## Objective

Turn Value Flow into a focused, progressively expandable intraprocedural value investigator that explains where an indexed value comes from and where supported static relations show it can flow.

## In scope

- Deterministic parameter, definition and use starting points using existing stable DFG node IDs.
- Root-first search and selection without rendering a broad repository DFG by default.
- Comes from, Flows to and Both controls mapped to existing traversal direction.
- Bounded one-hop progressive expansion, focus reset and frontier/leaf states.
- Semantic value roles and readable relation labels without changing stored graph types.
- Left-to-right origin-to-use layout using the existing deterministic layout and direct manipulation utilities.
- Node and edge inspectors with source, support, provenance, index and explicit static-analysis limitations.
- Honest initial, empty, limited, unresolved and unsupported states plus a complete keyboard-accessible relation list.

## Out of scope

- Parser, resolver, DFG producer, persistence, migration or dependency changes.
- New return-value, call-result, expression-transformation, type-inference, mutation, alias, field-read/write or interprocedural facts.
- Taint analysis, source/sink/sanitizer classification, runtime tracing or vulnerability conclusions.
- Calibrated probability or complete runtime-use claims.

## Existing code to reuse

- Server-bounded seed and neighbor projection patterns in `GraphProjectionService`.
- Progressive Dependency, Request Flow and Call Flow workspace state, merge, layout, inspector and accessibility helpers.
- Existing graph panning and node-drag interactions.

## Implementation sequence

1. Add deterministic DFG seed and one-hop neighbor projection behavior with existing budgets and metadata.
2. Add the dedicated progressive Value Flow workspace and semantic presentation.
3. Add backend and frontend regression coverage for root-first, direction, expansion, evidence and empty/limited states.
4. Run all declared gates and record exact results and remaining analyzer limitations.

## Data/API compatibility and migration

No schema or migration changes. Existing graph request and response fields remain compatible. Stored `dfg_node` and `dfg_*` types remain authoritative; semantic labels are projection/UI presentation only.

## Failure, security, performance, and observability requirements

Traversal remains deterministic, repository/index scoped and bounded by existing server maxima. Missing or partial static evidence is disclosed and never converted into a runtime or security conclusion.

## Required tests and commands

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest ..\tests\test_graph_projection.py -q
Set-Location ..\frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- backend/app/services/graph/graph_projection_service.py frontend/src/hooks/useAppController.ts frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx frontend/src/styles/pages/workspace.css frontend/src/types/api.ts tests/test_graph_projection.py docs/15-plans/task-register.md docs/16-agent-tasks/production-ux/UI-018-progressive-value-flow-explorer.md docs/18-production-evidence/progressive-value-flow-report.md
```

## Acceptance criteria

- Opening Value Flow shows bounded searchable value candidates and no arbitrary broad DFG canvas.
- Selecting a value presents supported origins and uses with user-facing direction language and a visually stable root.
- Continuing from a frontier adds one bounded hop without duplicate nodes/edges; focusing another value intentionally resets accumulated state.
- Nodes expose parameter, definition or use roles and relations use readable verbs without claiming unsupported value semantics.
- Inspectors and empty states disclose intraprocedural inferred static support, provenance, bounded coverage and unknown runtime behavior.
- Keyboard users retain complete controls and relation-list access, while pointer users retain canvas pan and node drag.

## Rollback

Revert the UI-018 files as one change. Existing generic data-flow routing remains API-compatible and can be restored without a data migration.

## Documentation and evidence updates

Record exact local verification results and remaining analyzer limitations in `docs/18-production-evidence/progressive-value-flow-report.md`. Keep this task in progress until every declared gate passes.

## Current verification state

Completed and locally verified on 2026-07-15. The focused graph projection suite passes 18 tests, the focused GraphPage suite passes 22 tests, all 82 frontend tests pass, ESLint and TypeScript pass, the Vite production build succeeds with 145 transformed modules, and declared diff hygiene passes. Interprocedural binding, transformations, mutation/type analysis, taint semantics and runtime claims remain explicitly unsupported.
