---
id: UI-002
title: Move frontend server state to feature queries and scoped mutations
status: completed
priority: P0
phase: 6
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [UI-001]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
decisions: []
technology_docs:
  - docs/03-technology/stack-overview.md
allowed_paths:
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/src/main.tsx
  - frontend/src/App.tsx
  - frontend/src/AppRoutes.tsx
  - frontend/src/App.test.tsx
  - frontend/src/api/client.ts
  - frontend/src/api/client.test.ts
  - frontend/src/api/server.ts
  - frontend/src/components/common/AsyncState.tsx
  - frontend/src/features/server-state/**
  - frontend/src/hooks/useAppController.ts
  - frontend/src/hooks/useImportController.ts
  - frontend/src/hooks/useImportController.test.tsx
  - frontend/src/styles/components.css
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/15-plans/phases/phase-6-production-ux.md
  - docs/16-agent-tasks/production-ux/UI-002-feature-query-server-state.md
  - docs/18-production-evidence/frontend-server-state-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/**
  - frontend/src/pages/**
  - frontend/src/routing/**
  - tests/fixtures/**
  - storage/**
dependency_changes:
  allowed: true
  add:
    - "@tanstack/react-query==5.101.2"
  remove: []
production_gates:
  - TanStack Query owns all current remote repository/workspace reads and request mutations.
  - Query keys retain repository and active index-version ownership; mutations invalidate only affected key families.
  - Superseded queries receive AbortSignal cancellation, retry policy is bounded/classified, and index polling stops at terminal states and while hidden.
  - Applicable loading, refreshing, empty, stale, permission, retryable-error, terminal-error, cancelled and unavailable states are explicit without discarding safe cached data.
  - Existing API payloads, URL ownership and visible page behavior remain compatible.
  - Frontend targeted tests, full tests, lint, typecheck and clean production build pass.
evidence_outputs:
  - docs/18-production-evidence/frontend-server-state-report.md
---

# Task UI-002 — Move Server State to Feature Queries

## Context

`UI-001` made the URL authoritative for navigation, but `useAppController` still copies remote repositories, overview, index status, graph, file, evidence, search and impact payloads into local state and manually coordinates fetch effects and fixed polling. Import and action flows also refetch broad state imperatively. This conflicts with the accepted TanStack Query ownership boundary and makes cancellation, retry, cache freshness and invalidation difficult to reason about.

## Objective

Make TanStack Query the sole owner of current frontend server state through typed feature queries and scoped mutations while preserving React Router URL ownership, existing endpoints, payloads, page components and local interaction state.

## In scope

- Add the exact accepted TanStack Query runtime dependency and one application QueryClient provider.
- Add typed query-key factories carrying repository and active index-version identity where applicable.
- Move repository list, overview, index status, graph, file tree, file content and evidence reads to cancellable query functions.
- Move search, impact, chat, graph expansion, re-index, pause/resume/cancel, delete and import-session actions to mutations.
- Keep upload selection/progress, form drafts, chat input and other transient interaction state local; store returned remote payloads in query/mutation state rather than duplicating them.
- Implement bounded retry/error classification, exponential retry delay with deterministic jitter, focus reconnect behavior and safe cached-data retention.
- Replace fixed manual indexing polling with query-owned polling that stops on terminal states and while the document is hidden.
- Invalidate only repository/list/status/version-owned query families affected by successful mutations.
- Expose a typed async-state projection and accessible loading/refreshing/stale/permission/retryable/terminal/cancelled recovery UI for the active surface.
- Add focused tests for query keys, cancellation, retry classification, polling, invalidation, cache retention and application compatibility.
- Record dependency, bundle, test and behavior evidence.

## Out of scope

- Backend endpoints, schemas, response fields, persistence or authentication changes.
- New page-specific read models, full UI redesign or route changes.
- Bounded graph projection/layout work (`UI-003`), architecture/tour/diff UX (`UI-004`) or real evaluation/settings/status integration (`UI-005`).
- Adding MSW, Playwright, Zustand, another state library, service worker or event-stream transport.
- Inventing retry headers, capability states or release performance thresholds absent from current responses/evidence.
- Treating local form/selection/display state as server state.

## Existing code to reuse

- `requestJson` timeout and error-cause behavior plus the current API paths in `useAppController` and `useImportController`.
- UI-001 canonical route identity and direct-link behavior.
- Existing repository/index/file/evidence types and page components.
- Existing Vitest/jsdom/Testing Library harness and application fetch fixtures.

## Implementation sequence

1. Capture the current lock, targeted/full test, lint and typecheck baseline.
2. Add `@tanstack/react-query==5.101.2`, configure one QueryClient and document its retry/freshness defaults.
3. Extract signal-aware API functions and repository/version-owned query-key factories.
4. Implement read hooks, status polling and typed async-state projection with focused policy tests.
5. Implement scoped mutation hooks and invalidation; migrate app/import controllers without changing page contracts.
6. Add application tests for cancellation, cache retention, refresh/error recovery and mutation invalidation.
7. Run clean install, targeted/full tests, lint, typecheck and a production build from a worktree without local environment files.
8. Update baseline, phase, evidence, project status and this task only after every local gate passes.

## Data/API compatibility and migration

No API or persisted-data migration is allowed. Query keys are client-only and version-scoped; current backend endpoints remain authoritative. Local state that duplicated remote payloads is removed. Rollback restores the imperative controller reads/actions, removes the provider/hooks and removes TanStack Query through npm.

## Failure, security, performance and observability requirements

- Every query function forwards TanStack's `AbortSignal`; cancellation is not surfaced as a terminal user error.
- Retry is disabled for permission/not-found/validation failures, bounded for retryable transport/timeout/5xx/429 failures, and uses a capped deterministic-jitter delay.
- Cached successful data may remain visible during refresh only with an explicit refreshing/stale state; cross-repository data is never used as fallback.
- Query/mutation errors expose safe classified messages only and do not include host paths, credentials, imported content or unrestricted payloads.
- Polling stops for completed, warning-completed, failed and cancelled jobs and pauses while hidden; focus/reconnect may refresh stale active data.
- No mutation clears or invalidates unrelated repository/version caches.

`@tanstack/react-query@5.101.2` is MIT licensed and implements the already accepted server-state choice. It adds no transport or persistence backend. Bundle cost is measured against UI-001 and recorded without inventing a release threshold.

## Required tests and commands

Run from `frontend/` on Node `>=24,<25` and npm `>=11,<12`:

```powershell
node --version
npm.cmd --version
npm.cmd install --save-exact @tanstack/react-query@5.101.2
$lockHash = (Get-FileHash package-lock.json -Algorithm SHA256).Hash
npm.cmd ci
if ((Get-FileHash package-lock.json -Algorithm SHA256).Hash -ne $lockHash) { throw 'npm ci mutated package-lock.json.' }
npm.cmd run test -- src/features/server-state src/App.test.tsx src/api/client.test.ts src/hooks/useImportController.test.tsx
npm.cmd run test
npm.cmd run lint
npx.cmd tsc -b
npm.cmd run build
```

Run from the repository root:

```powershell
git diff --check -- frontend docs
```

The production build must run from a clean checkout/worktree without ignored backend environment files. Expected results: stable lock, all targeted/full tests pass, lint has zero errors, TypeScript/build pass and whitespace validation passes.

## Acceptance criteria

- No remote repository/workspace payload is copied into controller `useState`; query or mutation state is the only client owner.
- Repository/list/status/overview/graph/file/evidence keys cannot collide across owners or active index versions.
- Direct route changes cancel superseded file/evidence queries through the supplied signal.
- Terminal/hidden index polling, classified bounded retry and retry-delay policy pass deterministic tests.
- Re-index/job/graph/delete/import mutations invalidate only documented affected query families.
- Active surfaces distinguish applicable loading, refreshing, empty, stale, unavailable, permission, retryable, terminal and cancelled states while retaining safe cached data during refresh.
- UI-001 route/direct-link/browser-history behavior and current request payloads remain compatible.
- The manifest/lock contain only the approved runtime dependency and deterministic transitive lock changes.
- Targeted/full tests, lint, typecheck, clean build and diff checks pass with results recorded in evidence.

## Rollback

Remove the provider, feature queries/mutations/state projection and TanStack Query dependency; restore the imperative controller requests and polling. No backend, schema, data or deployment rollback is required.

## Documentation and evidence updates

Update the source map, frontend test inventory, Phase 6 plan, project status, this task and `docs/18-production-evidence/frontend-server-state-report.md` with observed results and remaining UI-003 through UI-005/release gaps.

## Completion evidence

Completed locally on 2026-07-14. The exact dependency and lock are stable after `npm ci`; 22 targeted tests and all 38 frontend tests pass, with lint and TypeScript clean. A production build from detached commit `3c2987f` in an environment-free worktree passes with 131 transformed modules. Detailed ownership, invalidation, cancellation, retry, polling and bundle evidence is recorded in `docs/18-production-evidence/frontend-server-state-report.md`.
