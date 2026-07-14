---
id: UI-007
title: Deliver a compact evidence-aware overview and collapsible assistant drawer
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [UI-004]
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
  - frontend/src/AppRoutes.tsx
  - frontend/src/components/chat/AssistantChat.tsx
  - frontend/src/components/layout/AppShell.tsx
  - frontend/src/pages/workspace/OverviewPage.tsx
  - frontend/src/pages/workspace/WorkspaceLayout.tsx
  - frontend/src/pages/workspace/UI007Overview.test.tsx
  - frontend/src/styles/layout.css
  - frontend/src/styles/pages/workspace.css
  - docs/16-agent-tasks/production-ux/UI-007-compact-overview-assistant-drawer.md
  - docs/18-production-evidence/compact-overview-assistant-report.md
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
  - Overview uses current indexed signals without presenting a fixed four-layer architecture as repository fact.
  - The assistant drawer is keyboard accessible, collapsible, and leaves the Overview useful while closed.
  - Suggested questions live inside the assistant experience rather than consuming a separate Overview panel.
  - Key modules and recommended reading remain compact, justified, and expandable without long default lists.
  - Workspace search and index status remain visually separated at supported responsive widths.
evidence_outputs:
  - docs/18-production-evidence/compact-overview-assistant-report.md
---

# Task UI-007 — Compact Overview and assistant drawer

## Context

The owner accepted a visual direction that replaces the long Overview dashboard with a compact architecture summary, recommended reading, key modules, and a VS Code-like assistant drawer. The current Overview hard-codes four generic layers, duplicates suggested questions outside chat, and exposes long lists. The workspace index status also competes visually with search at constrained widths.

## Objective

Make the indexed repository Overview concise and evidence-aware while providing a collapsible contextual assistant and preserving existing routes, API contracts, conversation state, and Graph Explorer as the detailed relationship surface.

## In scope

- Replace the fixed four-layer architecture strip with a compact view derived from current overview signals and explicit uncertainty language.
- Keep the detailed relationship investigation in Graph View and preserve its navigation action.
- Present at most four recommended files and four modules initially, with explicit expand/collapse controls.
- Move suggested questions into the assistant drawer.
- Add an accessible assistant drawer toggle and responsive closed/open layout.
- Separate workspace index status from global search and remove duplicate diagnostic counts from the sidebar card.

## Out of scope

- New backend architecture classification, graph relations, APIs, schemas, persistence, retrieval, or dependencies.
- Claiming functional relationships that the current Overview response cannot prove.
- Redesigning Graph, Import, Projects, Index Jobs, Evaluation, or Settings.

## Existing code to reuse

- `OverviewPage`, `AssistantChat`, `AssistantWorkspace`, `WorkspaceShell`, current overview DTO, routes, query ownership, and UI-004 graph navigation.

## Implementation sequence

1. Add focused tests for compact lists, dynamic signals, assistant collapse, suggestions, and workspace status/search separation.
2. Refactor Overview presentation and guided-tour entry without changing the response contract.
3. Add the collapsible assistant drawer and responsive layout.
4. Run the frontend verification gates and record evidence.

## Data/API compatibility and migration

No API, schema, route, dependency, or migration change is authorized. Architecture cards are a deterministic presentation of current module, endpoint, stack, and important-file signals; unknown relationships remain explicitly unknown until inspected in Graph View.

## Failure, security, performance, and observability requirements

- Do not render source contents or host paths.
- Drawer controls must expose accessible labels, expanded state, visible focus, and usable closed-state recovery.
- Do not silently hide more than the compact default; provide a visible expand action.
- No animation may be required to access content, and reduced-motion behavior remains intact.

## Required tests and commands

```powershell
Set-Location frontend
npm.cmd test -- --run src/pages/workspace/UI007Overview.test.tsx src/pages/workspace/UI004Workspace.test.tsx src/App.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- frontend docs
```

Record exact results in `docs/18-production-evidence/compact-overview-assistant-report.md`.

## Acceptance criteria

- Overview no longer labels every repository with the same four architecture layers.
- Architecture, reading, and module summaries remain traceable to current indexed signals and disclose missing relationship evidence.
- Suggested questions are available inside the assistant drawer and populate the existing composer.
- The drawer opens, closes, and reports its state accessibly.
- Recommended Reading and Key Modules show no more than four rows by default and can reveal all returned items.
- Index Status does not overlap or visually merge with global search across the existing responsive breakpoints.
- Targeted/full frontend tests, lint, typecheck, build, and diff hygiene pass.

## Rollback

Restore the prior Overview panels and always-open assistant side panel. No data rollback is required.

## Documentation and evidence updates

Update this task and `docs/18-production-evidence/compact-overview-assistant-report.md` with exact verification results. Do not claim backend architecture classification.

## Verification

Completed locally on 2026-07-14. The targeted UI-007/UI-004/App regression set passes 16 tests, the full frontend suite passes 59 tests across 11 files, ESLint and TypeScript pass, and the Vite production build succeeds. Diff hygiene passes for `frontend` and `docs`. Architecture cards are explicitly module signals from the current Overview contract; relationship evidence remains delegated to Graph Explorer. The project owner retains final visual acceptance in the running application.
