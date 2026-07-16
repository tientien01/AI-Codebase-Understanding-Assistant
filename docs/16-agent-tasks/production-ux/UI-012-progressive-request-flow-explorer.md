---
id: UI-012
title: Add focused progressive request-flow exploration
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-010, UI-011]
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
  - tests/test_graph_projection.py
  - docs/16-agent-tasks/production-ux/UI-012-progressive-request-flow-explorer.md
  - docs/18-production-evidence/progressive-request-flow-report.md
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
  - Request Flow starts from deterministic server-endpoint and client-call entry points rather than an unrelated broad node slice.
  - Expansion is one bounded hop from an explicit node and preserves honest static-support, truncation and continuation language.
  - Call-site nodes remain available as indexed evidence but do not dominate the default request-path canvas.
  - Client-call, endpoint, handler and downstream-call relations remain visibly distinct without claiming runtime order or complete traces.
  - The workspace uses one graph-first view with entry-point reset, path controls, inspector and accessible relation alternative.
  - Existing server maxima, repository/index ownership, deterministic ordering and no-dangling-edge invariants remain enforced.
  - Focused backend/frontend tests, typecheck, production build and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/progressive-request-flow-report.md
---

# Task UI-012 — Progressive Request Flow Explorer

## Context

The current Request Flow requests a broad repository projection before the user selects an endpoint or client API call. Node-budget ordering can include dozens of isolated call-site nodes while excluding their function or endpoint counterparts, producing a large canvas with zero included relations.

The project owner authorized this task in the active conversation on 2026-07-15. The accepted graph and workspace contracts remain authoritative.

## Objective

Make Request Flow a focused static-path explorer that begins with meaningful request entry points and expands one supported hop at a time in the same workspace.

## In scope

- Deterministic server-endpoint and client API-call starting points using existing graph facts.
- Rooted one-hop upstream, downstream or supported-full-path expansion with existing budgets and continuation metadata.
- Default suppression of call-site presentation on the primary canvas while retaining direct resolved `calls` relations.
- One-view entry-point overview, search, path controls, graph canvas, inspector and relation-list fallback.
- Honest labels for `calls_api`, `exposes_endpoint` and `calls` without runtime-sequence claims.
- Focused regression tests and production evidence.

## Out of scope

- Parser, resolver, graph producer, persistence, migration or dependency changes.
- New framework, method-aware client matching, call-site evidence linkage, runtime tracing, database operations or response-flow claims.
- External-service certainty, complete request traces or path membership not supported by the current graph.

## Required tests and commands

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest ..\tests\test_graph_projection.py -q
Set-Location ..\frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- backend/app/services/graph/graph_projection_service.py frontend/src/hooks/useAppController.ts frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx frontend/src/styles/pages/workspace.css tests/test_graph_projection.py docs/16-agent-tasks/production-ux/UI-012-progressive-request-flow-explorer.md docs/18-production-evidence/progressive-request-flow-report.md
```

## Acceptance criteria

- Initial Request Flow displays bounded endpoint/client-call entry points with stable reason labels and no unrelated full-repository call-site slice.
- Selecting an entry point opens a supported static path; continuing from a visible node adds one bounded hop with no duplicate nodes or edges.
- Upstream, downstream and supported-full-path controls reset incompatible accumulated state and use user-facing semantics.
- Call-site nodes do not appear on the default canvas, and UI labels `exposes_endpoint` as `Handled by` without renaming stored graph truth.
- Empty, limited, unmatched and unresolved states avoid claiming that absent static support proves absent runtime behavior.
- The inspector and complete relation list remain keyboard accessible in the same workspace.

## Documentation and evidence updates

Record exact focused verification results and remaining producer/schema limitations in `docs/18-production-evidence/progressive-request-flow-report.md`. Keep the task in progress until the declared gates pass.
