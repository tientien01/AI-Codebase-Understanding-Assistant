---
id: UI-022
title: Preserve Code Explorer context and embed source-launched Value Trace
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [UI-002, UI-009, UI-021, INT-006]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
allowed_paths:
  - frontend/src/App.tsx
  - frontend/src/App.test.tsx
  - frontend/src/AppRoutes.tsx
  - frontend/src/api/server.ts
  - frontend/src/components/code/FileTree.tsx
  - frontend/src/components/code/FileTree.test.tsx
  - frontend/src/components/layout/AppShell.tsx
  - frontend/src/components/layout/AppShell.test.tsx
  - frontend/src/features/server-state/queries.ts
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/CodeExplorerPage.tsx
  - frontend/src/pages/workspace/CodeExplorerPage.test.tsx
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/routing/routes.ts
  - frontend/src/routing/routes.test.ts
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - frontend/src/utils/valueTrace.ts
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/production-ux/UI-022-code-explorer-trace-continuity.md
  - docs/18-production-evidence/code-explorer-trace-continuity-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - frontend/package.json
  - frontend/package-lock.json
  - storage/**
dependency_changes:
  allowed: false
production_gates:
  - Repository folders are keyboard-operable collapsible tree items; search reveals matches without destroying the prior expansion state.
  - Selecting a deep file retains tree expansion and scroll while only the source reader reports loading.
  - Repository-scoped last source, selected line, tree scroll and per-file source scroll survive Code/Graph navigation without host-path leakage.
  - A source-launched Value Trace opens inside Code Explorer, retains progressive bounded expansion, and offers an explicit full-graph transition and source return.
  - Focused/full frontend tests, lint, typecheck, production build and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/code-explorer-trace-continuity-report.md
---

# Task UI-022 — Code Explorer and Value Trace Continuity

## Context

The owner reported that the current file tree renders every descendant, resets to the top after a deep file selection, loses source position after a Value Trace transition, and makes repeated Code/Graph switching cumbersome. The owner authorized one combined task in the active conversation on 2026-07-16.

## Objective

Turn Code Explorer into a stateful source workspace with a collapsible persistent tree, non-blocking file changes, source-position restoration and an embedded source-launched Value Trace panel.

## In scope

- Add accessible folder expand/collapse, Collapse all and Reveal active file behavior.
- Preserve repository-scoped expansion/tree scroll and per-file source scroll as transient session state.
- Keep the Code Explorer shell mounted while a different file is loading.
- Put selected file and line in the canonical Code route and retain the last Code destination in workspace navigation.
- Embed the existing progressive Value Trace for source-launched token context and provide close/full-graph/back-to-source actions.
- Preserve graph query ownership, bounded expansion, limitation language and deep-link recovery.

## Out of scope

- Backend graph, parser, DFG or API response changes.
- Monaco/editor dependencies, file editing, tabs with unsaved buffers or multi-window state.
- Semantic-token replacement, new Value Trace semantics or cross-repository flow.
- Persisting transient UI state in the database.

## Existing code to reuse

- React Router canonical Code/Graph routes and Value Trace context encoding.
- TanStack Query graph/file queries and cache keys.
- `ProgressiveValueFlow` behavior, graph expansion and accessible relation list.
- Existing Code Explorer source reader and session-persistent sidebar pattern.

## Implementation sequence

1. Make FileTree controlled by persistent repository-scoped expansion and scroll state.
2. Retain file content during selection changes and restore source position deterministically.
3. Extend the Code route with source-launched trace context and retain last source navigation.
4. Reuse the progressive Value Trace as an embedded panel with full-graph/source transitions.
5. Add focused regressions and run all declared frontend gates.

## Data/API compatibility and migration

No server or schema change. The optional percent-encoded `trace` Code query parameter reuses `value-context:v1`; existing Code and Graph URLs remain valid.

## Failure, security, performance, and observability requirements

- Session keys contain only repository ID, repository-relative paths, line and scroll/expansion state.
- Invalid trace roots fail closed to the normal Code workspace.
- File search and selection do not expand the complete unfiltered repository tree in the DOM.
- Loading a new file retains visibly stale source only with a loading-selection indicator.
- Graph limits and one-hop expansion remain server-owned.

## Required tests and commands

```powershell
Set-Location frontend
npm.cmd test -- --run src/components/code/FileTree.test.tsx src/pages/workspace/CodeExplorerPage.test.tsx src/pages/workspace/GraphPage.test.tsx src/routing/routes.test.ts src/components/layout/AppShell.test.tsx src/App.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/AppRoutes.tsx frontend/src/api/server.ts frontend/src/components/code/FileTree.tsx frontend/src/components/code/FileTree.test.tsx frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/AppShell.test.tsx frontend/src/features/server-state/queries.ts frontend/src/hooks/useAppController.ts frontend/src/pages/workspace/CodeExplorerPage.tsx frontend/src/pages/workspace/CodeExplorerPage.test.tsx frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx frontend/src/routing/routes.ts frontend/src/routing/routes.test.ts frontend/src/styles/pages/workspace.css frontend/src/types/api.ts frontend/src/utils/valueTrace.ts docs/15-plans/task-register.md docs/16-agent-tasks/production-ux/UI-022-code-explorer-trace-continuity.md docs/18-production-evidence/code-explorer-trace-continuity-report.md
```

## Acceptance criteria

- A collapsed folder hides descendants and retains its state after file selection and Code/Graph navigation.
- Selecting a file below the initial tree viewport does not reset tree scroll or flash a page-level loading replacement.
- Returning from Value Trace restores the originating file, selected line and source scroll.
- Source-launched trace expansion is usable without leaving Code Explorer; full graph and back-to-source preserve the same context.
- All declared verification commands pass.

## Rollback

Remove the optional Code trace parameter and embedded panel; existing canonical Code/Graph routes and server queries remain compatible.

## Documentation and evidence updates

Record behavior, state ownership, limitations and exact verification in `docs/18-production-evidence/code-explorer-trace-continuity-report.md`.
