---
id: UI-019
title: Unify sidebar navigation and completed-index workspace readiness
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-001, UI-002, UI-005, UI-006, UI-017]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
allowed_paths:
  - frontend/src/App.test.tsx
  - frontend/src/components/layout/AppShell.tsx
  - frontend/src/components/layout/AppShell.test.tsx
  - frontend/src/config/navigation.ts
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/management/IndexingPage.tsx
  - frontend/src/styles/layout.css
  - frontend/src/utils/repository.ts
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/production-ux/UI-019-unified-navigation-index-readiness.md
  - docs/18-production-evidence/unified-navigation-index-readiness-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/**
  - frontend/package.json
  - frontend/package-lock.json
dependency_changes:
  allowed: false
production_gates:
  - Management and workspace sidebars share one persistent collapse state and the same accessible toggle behavior.
  - Switching between management and workspace routes does not reset the chosen sidebar state.
  - Settings remains a single global management destination and is absent from repository workspace navigation.
  - A successful terminal index status with an active index version can bridge a stale repository-list cache until the invalidated repository query refreshes.
  - Progress alone never authorizes workspace access; failed, cancelled, versionless or non-terminal jobs remain unusable.
  - Frontend focused/full tests, lint, typecheck, production build and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/unified-navigation-index-readiness-report.md
---

# Task UI-019 — Unified Navigation and Index Readiness

## Objective

Make sidebar behavior consistent across management and repository workspaces, remove the duplicate workspace Settings entry, and prevent a completed versioned index from remaining temporarily locked behind stale repository-list state.

## In scope

- One local persistent sidebar preference and accessible collapse control for both shells.
- Icon-only labels/tooltips and compact layout in both management and workspace modes.
- Removal of Settings from `workspaceNav`; the global management Settings route remains unchanged.
- Deterministic reconciliation of a successful terminal `IndexStatus` carrying a positive `index_version` with stale repository-list data while the existing invalidation refreshes server state.
- Focused regression tests for persistence across shells, navigation uniqueness and safe index-readiness reconciliation.

## Out of scope

- Backend index activation, repository persistence, API schemas, Settings content or mutation support.
- Treating 100% progress without successful terminal state and active version as usable.
- New dependencies or route vocabulary.

## Required verification

```powershell
Set-Location frontend
npm.cmd test -- --run src/components/layout/AppShell.test.tsx src/App.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- frontend/src/App.test.tsx frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/AppShell.test.tsx frontend/src/config/navigation.ts frontend/src/hooks/useAppController.ts frontend/src/pages/management/IndexingPage.tsx frontend/src/styles/layout.css frontend/src/utils/repository.ts docs/15-plans/task-register.md docs/16-agent-tasks/production-ux/UI-019-unified-navigation-index-readiness.md docs/18-production-evidence/unified-navigation-index-readiness-report.md
```

## Acceptance criteria

- Collapsing either sidebar and navigating to the other shell preserves the collapsed icon rail; expanding works symmetrically.
- Workspace navigation contains no Settings link, while management navigation contains exactly one global Settings link.
- Completed and completed-with-warnings job status unlocks the workspace only when it carries a positive index version.
- Running, failed, cancelled, versionless and progress-only states never unlock workspace routes.
- Existing repository query invalidation remains the long-lived source refresh; reconciliation is only a terminal-state cache bridge.

## Documentation and evidence updates

Record exact local verification in `docs/18-production-evidence/unified-navigation-index-readiness-report.md`. Keep the task in progress until every declared gate passes.

## Current verification state

Completed and locally verified on 2026-07-15. Focused App/AppShell coverage passes 15 tests, all 86 frontend tests pass, ESLint and TypeScript pass, the Vite production build succeeds with 145 transformed modules, and declared diff hygiene passes. Workspace access remains fail-closed for progress-only, failed, cancelled, mismatched and versionless index state.
