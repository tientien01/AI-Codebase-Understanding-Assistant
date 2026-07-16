---
id: UI-021
title: Replace global Value Flow browsing with contextual Value Trace
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-003, UI-009, UI-012, UI-015, UI-018]
requirements: []
contracts:
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
allowed_paths:
  - backend/app/services/graph/graph_projection_service.py
  - frontend/src/AppRoutes.tsx
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/CodeExplorerPage.tsx
  - frontend/src/pages/workspace/CodeExplorerPage.test.tsx
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/styles/pages/workspace.css
  - frontend/src/utils/valueTrace.ts
  - tests/test_graph_projection.py
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/production-ux/UI-021-contextual-value-trace.md
  - docs/18-production-evidence/contextual-value-trace-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/app/services/parsing/**
  - backend/app/services/code_analysis/**
  - backend/app/services/indexing/**
  - frontend/package.json
  - frontend/package-lock.json
  - storage/**
dependency_changes:
  allowed: false
production_gates:
  - Value Trace is absent from the primary relationship tabs and global question chooser.
  - Code Explorer offers identifier-level trace actions bound to repository-relative file and line context.
  - Request and Call Flow offer scope-level trace actions from selected endpoint/function nodes.
  - Server resolution returns only deterministic indexed DFG candidates matching the supplied context and never invents a relation.
  - A direct/deep-linked data-flow route without context explains where to start instead of browsing repository-wide values.
  - Resolved candidates retain progressive one-hop expansion, evidence, limitations, keyboard access, pan and node drag.
  - Focused backend/frontend tests, full frontend tests, lint, typecheck, build and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/contextual-value-trace-report.md
---

# Task UI-021 — Contextual Value Trace

## Objective

Keep the deterministic Value Flow engine while replacing repository-wide value browsing with contextual traces launched from source code, request endpoints and callable nodes.

## In scope

- Remove Value Flow from primary graph navigation and the global relationship chooser.
- Encode bounded file/line/name or file/range context in the existing graph root vocabulary.
- Resolve context against indexed DFG nodes on the server with deterministic ordering and existing budgets.
- Add identifier actions to Code Explorer and scope actions to selected Request/Call Flow nodes.
- Rename the focused surface to Value Trace and show a guidance state when no context is supplied.
- Preserve current direction, expansion, inspector, accessibility and canvas interactions after a candidate is selected.

## Out of scope

- Parser/DFG producer changes, cross-function flow, transformations, taint semantics or runtime claims.
- New dependencies, API fields, database schema or migration.
- Automatic semantic binding between a call argument and callee parameter.

## Required verification

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/test_graph_projection.py -q
backend\.venv\Scripts\python.exe -m pytest tests/test_codebase_service.py -q
Set-Location frontend
npm.cmd test -- --run src/pages/workspace/CodeExplorerPage.test.tsx src/pages/workspace/GraphPage.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- backend/app/services/graph/graph_projection_service.py frontend/src/AppRoutes.tsx frontend/src/hooks/useAppController.ts frontend/src/pages/workspace/CodeExplorerPage.tsx frontend/src/pages/workspace/CodeExplorerPage.test.tsx frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx frontend/src/styles/pages/workspace.css frontend/src/utils/valueTrace.ts tests/test_graph_projection.py docs/15-plans/task-register.md docs/16-agent-tasks/production-ux/UI-021-contextual-value-trace.md docs/18-production-evidence/contextual-value-trace-report.md
```

## Current verification state

Completed and locally verified on 2026-07-15. Context resolution passes 19 graph projection tests and the 28-test service integration suite. Code Explorer and GraphPage pass 27 focused tests; all 91 frontend tests, lint, TypeScript, production build and declared diff hygiene pass. Cross-function binding, transformations, taint semantics and runtime claims remain explicitly unsupported.
