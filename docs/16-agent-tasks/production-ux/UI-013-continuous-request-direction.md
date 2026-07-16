---
id: UI-013
title: Preserve Request Flow focus across direction changes
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-012, INT-005]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
technology_docs:
  - docs/03-technology/stack-overview.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - docs/16-agent-tasks/production-ux/UI-013-continuous-request-direction.md
  - docs/18-production-evidence/continuous-request-direction-report.md
forbidden_paths:
  - backend/**
  - frontend/package.json
  - frontend/package-lock.json
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Changing request direction preserves the current selected node and does not return to entry points.
  - The active node is reprojected in the selected direction with existing one-hop budgets and deterministic server facts.
  - Direction-specific terminal messages distinguish indexed boundaries, unmatched endpoints, unresolved handlers, callers, and callees.
  - Focused frontend tests, lint, typecheck, build, and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/continuous-request-direction-report.md
---

# UI-013 - Continuous Request Direction

## Context

Request Flow currently clears the active path, selection, inspector, and layout whenever Upstream or Downstream changes. The reset prevents mixed projections but breaks investigation continuity. Generic `No more supported hops` text also hides whether a node is a natural boundary or has unresolved static support.

The project owner authorized this correction in the active conversation on 2026-07-15.

## Objective

Treat direction as a lens over the current request entity rather than navigation back to entry points, while retaining bounded one-hop projection and honest static-analysis language.

## Required verification

```powershell
Set-Location frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx docs/16-agent-tasks/production-ux/UI-013-continuous-request-direction.md docs/18-production-evidence/continuous-request-direction-report.md
```

## Acceptance criteria

- Direction changes with no active path only update the preferred direction.
- Direction changes with an active selection keep that selection, reroot the visible path there, and load one bounded hop in the new direction.
- The user returns to entry points only through the explicit reset action or entry-scope change.
- Terminal labels explain the current node/direction boundary without claiming runtime absence.
