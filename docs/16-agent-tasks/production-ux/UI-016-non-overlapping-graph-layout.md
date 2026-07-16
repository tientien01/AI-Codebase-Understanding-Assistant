---
id: UI-016
title: Prevent node overlap and reduce edge crossings across Graph View
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-011, UI-012, UI-015]
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
allowed_paths:
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/styles/pages/workspace.css
  - docs/16-agent-tasks/production-ux/UI-016-non-overlapping-graph-layout.md
  - docs/18-production-evidence/non-overlapping-graph-layout-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/**
  - frontend/package.json
  - frontend/package-lock.json
dependency_changes:
  allowed: false
production_gates:
  - Shared progressive layouts never place visible node rectangles on top of each other.
  - Incoming, root and outgoing hops receive distinct deterministic columns with dynamic canvas width.
  - Node ordering reduces avoidable edge crossings while preserving deterministic output and stable progressive positions.
  - Self-loops, reverse edges and dense siblings remain visible and keyboard-accessible.
  - Dependencies, Request Flow, Call Flow and legacy graph regressions pass without a new graph dependency.
evidence_outputs:
  - docs/18-production-evidence/non-overlapping-graph-layout-report.md
---

# Task UI-016 — Non-overlapping Graph Layout

## Objective

Replace fixed-width, boundary-clamped progressive placement with a deterministic layered layout shared by Graph View modes, guaranteeing node separation and reducing avoidable edge crossings.

## Required verification

```powershell
Set-Location frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx frontend/src/styles/pages/workspace.css docs/16-agent-tasks/production-ux/UI-016-non-overlapping-graph-layout.md docs/18-production-evidence/non-overlapping-graph-layout-report.md
```

## Acceptance criteria

- Dense caller/callee, request and dependency fixtures have no intersecting node rectangles.
- Canvas width grows for additional hop columns instead of clamping nodes onto the root.
- Sibling order is deterministic and uses adjacent-neighbor position to reduce crossings.
- Zoom, fit, edge selection, inspectors and accessible relation lists continue to work.

## Current verification state

Completed and locally verified on 2026-07-15. The GraphPage suite passes 19 tests including a dense 9-caller/11-callee rectangle-intersection check and dynamic multi-hop canvas-width assertion. All 78 frontend tests, ESLint, TypeScript, production build and diff hygiene pass.
