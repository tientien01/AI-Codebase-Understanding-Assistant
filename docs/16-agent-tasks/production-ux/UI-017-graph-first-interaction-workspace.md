---
id: UI-017
title: Make Graph View graph-first with collapsible navigation and direct manipulation
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-016]
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
allowed_paths:
  - frontend/src/components/layout/AppShell.tsx
  - frontend/src/components/layout/AppShell.test.tsx
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/styles/layout.css
  - frontend/src/styles/pages/workspace.css
  - docs/16-agent-tasks/production-ux/UI-017-graph-first-interaction-workspace.md
  - docs/18-production-evidence/graph-first-interaction-workspace-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/**
  - frontend/package.json
  - frontend/package-lock.json
dependency_changes:
  allowed: false
production_gates:
  - Workspace navigation can collapse to an icon rail and restore without losing the current route.
  - Graph controls use materially less vertical space while preserving every action and accessible label.
  - Pointer dragging on empty canvas pans its viewport in both axes without requiring scrollbar manipulation.
  - Pointer dragging a node changes its local visual position and connected edges without triggering node selection.
  - Click, keyboard, zoom, fit, inspector and accessible relation alternatives remain functional.
  - Reduced-motion and touch/pointer behavior do not depend on animation or color alone.
evidence_outputs:
  - docs/18-production-evidence/graph-first-interaction-workspace-report.md
---

# Task UI-017 — Graph-first Interaction Workspace

## Objective

Give Graph View most of the viewport and support direct mouse/touch manipulation through a collapsible sidebar, compact contextual controls, canvas panning and draggable nodes.

## Required verification

```powershell
Set-Location frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx src/components/layout/AppShell.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/AppShell.test.tsx frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx frontend/src/styles/layout.css frontend/src/styles/pages/workspace.css docs/16-agent-tasks/production-ux/UI-017-graph-first-interaction-workspace.md docs/18-production-evidence/graph-first-interaction-workspace-report.md
```

## Acceptance criteria

- Sidebar toggle is keyboard accessible, exposes expanded state and retains icon tooltips when collapsed.
- Progressive and legacy graph canvases pan by dragging empty space and expose a visible interaction hint.
- All graph nodes can be dragged within canvas bounds; edge paths rerender from the new location.
- A drag gesture never invokes the node's click action; a normal click retains existing behavior.
- Compact graph header/toolbar leaves the canvas with the majority of the available workspace height.

## Current verification state

Completed and locally verified on 2026-07-15. The focused sidebar/GraphPage suites pass 21 tests, all 80 frontend tests pass, ESLint and TypeScript pass, the production build succeeds with 145 transformed modules, and declared diff hygiene passes.
