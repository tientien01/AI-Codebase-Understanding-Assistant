---
id: UI-009
title: Refine the Code Explorer workspace from the approved visual reference
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-002]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - frontend/src/components/common/Icon.tsx
  - frontend/src/components/code/FileTree.tsx
  - frontend/src/pages/workspace/CodeExplorerPage.tsx
  - frontend/src/pages/workspace/CodeExplorerPage.test.tsx
  - frontend/src/styles/pages/workspace.css
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/production-ux/UI-009-code-explorer-reference-workspace.md
  - docs/18-production-evidence/code-explorer-reference-workspace-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/**
  - backend/migrations/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Code Explorer prioritizes the source reader, while file tree, intelligence and assistant context remain available without nested scrolling.
  - File-tree, source, symbol, call-relationship and assistant controls use accessible text labels, icons and keyboard-native controls.
  - The contextual assistant remains available beside the workspace, and the Code Explorer remains usable at constrained viewport widths.
  - Existing source navigation, range loading, empty states and capability disclosures remain truthful.
evidence_outputs:
  - docs/18-production-evidence/code-explorer-reference-workspace-report.md
---

# UI-009 — Code Explorer reference workspace

## Context

The owner approved `05_code_explorer(1).png` as a visual reference for a denser, editor-first Code Explorer. The current page renders its source, file tree, intelligence and assistant areas as competing fixed columns and contains several weak empty states.

## Objective

Deliver a responsive Code Explorer that uses the approved reference for visual direction while preserving all existing server-backed source, intelligence and assistant behavior.

## In scope

- Reorganize the existing Code Explorer into an editor-first workspace with a searchable file tree, breadcrumbs, readable source header, and symbols/call sections alongside the existing contextual assistant drawer.
- Add consistent semantic icons using the existing icon component; preserve visible text labels and tooltips for icon-only controls.
- Improve source, intelligence and unavailable/empty states without fabricated graph, endpoint, evidence or assistant data.
- Add focused component coverage for the desktop and constrained layouts and assistant-drawer interaction.

## Out of scope

- New API endpoints, data-model changes, synthetic code intelligence, syntax parsing, external editor integration, or changes to assistant/retrieval behavior.

## Existing code to reuse

- Current Code Explorer API/query hooks, source navigation, range loading, assistant panel and shared icon primitives.
- The workspace interaction and page contracts named above.

## Data/API compatibility and migration

No API, persisted-data, route or migration change is permitted. Existing source/range, symbol, endpoint, relation and assistant payloads remain authoritative.

## Failure, security, performance, and observability requirements

- Empty, limited and unavailable states state their server-provided reason or the applicable file limitation; they never claim a planned capability is implemented.
- The reader remains usable at constrained widths; the page must not introduce nested scrolling regions for the file tree.
- Icon-only controls have accessible names and tooltips. Color is not the only status indicator.

## Required tests and commands

```powershell
Set-Location frontend
npm.cmd test -- --run src/pages/workspace/CodeExplorerPage.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- frontend docs
```

## Acceptance criteria

- The source reader receives the primary workspace width on a desktop viewport while the existing assistant remains available.
- The file tree has one scroll container, recognisable file/folder icons and labels, and no clipped essential navigation controls.
- Source, symbols, call relationships and related evidence display stable headings and truthful empty/limited states.
- Assistant context is visibly scoped to the current file or repository when supported by the existing payload.
- Focused tests, full frontend tests, lint, TypeScript build and production build pass.

## Rollback

Restore the prior `CodeExplorerPage` markup/styles and remove the UI-009-specific test and evidence report. No data rollback is required.

## Documentation and evidence updates

Record executed commands and observed results in `docs/18-production-evidence/code-explorer-reference-workspace-report.md`. Update this task only with verified results.
