---
id: UI-001
title: Add React Router and a reloadable deep-linked workspace
status: completed
priority: P0
phase: 6
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [FND-003]
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
  - frontend/src/routing/**
  - frontend/src/hooks/useAppController.ts
  - frontend/src/components/layout/AppShell.tsx
  - frontend/src/config/navigation.ts
  - frontend/src/pages/routing/**
  - frontend/src/pages/workspace/CodeExplorerPage.tsx
  - frontend/src/styles/layout.css
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/15-plans/phases/phase-6-production-ux.md
  - docs/16-agent-tasks/production-ux/UI-001-router-deep-linked-workspace.md
  - docs/18-production-evidence/frontend-navigation-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/**
  - frontend/src/api/**
  - frontend/src/pages/management/**
  - frontend/src/styles/pages/**
  - tests/fixtures/**
  - storage/**
dependency_changes:
  allowed: true
  add:
    - react-router-dom==7.18.1
  remove: []
production_gates:
  - React Router owns browser history and every canonical production-v1 route.
  - Repository workspace, file, symbol, endpoint, graph, impact, search, conversation, and evidence deep links survive reload.
  - Invalid or stale route context presents an explicit recovery action without exposing host paths or silently selecting unrelated content.
  - Existing management and workspace page behavior remains compatible.
  - Frontend targeted tests, full tests, lint, typecheck, and production build pass.
evidence_outputs:
  - docs/18-production-evidence/frontend-navigation-report.md
---

# Task UI-001 — Add Router and a Deep-Linked Workspace

## Context

The current SPA stores the active page and repository selection only in React component state. Refreshing, opening a new tab, browser back/forward, and sharing a source/evidence URL lose the user's workspace context. The accepted UX contract assigns URL/history ownership to React Router and defines the canonical production-v1 route set.

## Objective

Make every canonical management and repository workspace surface reloadable and shareable through React Router while preserving the current page components, API behavior, and visual language.

## In scope

- Add the exact approved React Router runtime dependency and mount one browser router at the application boundary.
- Define one typed canonical route parser/builder for management, repository, file, symbol, endpoint, graph, impact, search, conversation, evidence, evaluation, and settings routes.
- Replace page-state navigation in the application shell, project actions, indexing actions, workspace navigation, file selection, graph selection, search execution, impact execution, and citation opening with browser navigation.
- Restore repository and supported query/path state from a direct URL on first render and on browser back/forward.
- Preserve opaque/encoded repository, entity, evidence, and relative-path values; never place a host filesystem path in a URL.
- Render explicit not-found, missing-repository, unusable-repository, and unsupported-detail recovery states with deterministic next actions.
- Add targeted routing tests covering canonical resolution/building, direct deep links, navigation, recovery, and history behavior.
- Record dependency, bundle, test, and compatibility evidence.

## Out of scope

- TanStack Query/server-state migration (`UI-002`).
- New backend endpoints, API response fields, authentication, or repository authorization behavior.
- Graph projection/layout changes (`UI-003`), architecture/tour/diff UI (`UI-004`), or real evaluation/settings/status integration (`UI-005`).
- Redesigning existing pages, introducing a new design system, or changing page-specific styling.
- Implementing new symbol/endpoint/conversation read models; their canonical routes preserve identity and show an honest bounded recovery/availability state when current APIs cannot resolve the requested detail.
- Adding Playwright, MSW, TanStack Query, a global store, or any dependency other than the exact router package.

## Existing code to reuse

- Existing management/workspace page components in `frontend/src/pages/`.
- Existing application controller and API functions in `frontend/src/hooks/useAppController.ts`.
- Existing shell/navigation components and `Page` type.
- Existing Vitest, jsdom, and Testing Library setup established by `FND-005`.

## Implementation sequence

1. Capture the current frontend test/lint/typecheck/build baseline and lockfile hash.
2. Add `react-router-dom==7.18.1` and verify the lock change is limited to router packages.
3. Add typed canonical route resolution and URL builders, including safe parameter decoding and invalid-route classification.
4. Mount the router and derive application shell/page/repository context from the current location.
5. Route all existing navigation actions and supported page state through canonical URLs.
6. Add deterministic route recovery UI and direct-link restoration for file/search/graph/impact/evidence state.
7. Run targeted and full frontend gates in a clean environment that does not load local backend environment files.
8. Update the baseline, phase status, evidence, project status, and this task only after all gates pass.

## Data/API compatibility and migration

No API, persisted data, backend route, request, or response change is allowed. Existing page components and API calls remain the compatibility surface. Legacy `/` redirects once to canonical `/projects`; other invalid URLs do not silently redirect. The only migration is browser URL ownership from transient component state to the canonical route model.

## Failure, security, performance, and observability requirements

- Malformed percent encoding, missing route parameters, unknown routes, and repositories absent from the loaded owned list fail closed into recovery UI.
- Host source paths, secrets, raw imported content, and unrestricted provider output never enter route state or error output.
- Route navigation must not add duplicate server fetches beyond the existing Strict Mode development behavior.
- Route helpers are deterministic and independently tested; recovery output includes the requested safe identifier and an actionable destination.
- The evidence report records the production bundle output before/after the router addition; no numeric release budget is invented.

`react-router-dom@7.18.1` is MIT licensed, supports the repository's Node 24 runtime (`>=20` upstream), and implements the already accepted routing choice. Rollback removes the provider, route helpers/tests/recovery UI, restores page-state navigation, and removes the dependency through npm so the lock remains consistent.

## Required tests and commands

Run from `frontend/` on Node `>=24,<25` and npm `>=11,<12`:

```powershell
node --version
npm.cmd --version
npm.cmd install --save-exact react-router-dom@7.18.1
$lockHash = (Get-FileHash package-lock.json -Algorithm SHA256).Hash
npm.cmd ci
if ((Get-FileHash package-lock.json -Algorithm SHA256).Hash -ne $lockHash) { throw 'npm ci mutated package-lock.json.' }
npm.cmd run test -- src/routing/routes.test.ts src/App.test.tsx
npm.cmd run test
npm.cmd run lint
npx.cmd tsc -b
npm.cmd run build
```

Run from the repository root:

```powershell
git diff --check -- frontend docs
```

The production build must run from a clean checkout/worktree without ignored backend environment files. Expected results: lock stability, all targeted/full tests pass, lint reports zero errors, TypeScript and Vite production build pass, and whitespace validation passes.

## Acceptance criteria

- All canonical routes in the accepted interaction contract resolve deterministically and generate encoded shareable URLs.
- Browser back/forward and direct reload preserve the active page plus repository/file/search/graph/impact/evidence identity supported by current APIs.
- Navigation controls use links or router navigation and expose the active page accessibly.
- `/` reaches `/projects`; unknown, malformed, missing-repository, and unusable-repository workspace routes show explicit recovery instead of unrelated content.
- Direct evidence routes request only the URL-owned repository/evidence pair; direct code routes request the encoded relative path.
- Existing import, index, delete, search, impact, graph, assistant, and evidence actions retain their API requests and visible outcomes.
- The manifest/lock contain only the approved runtime dependency and deterministic transitive lock changes.
- Targeted/full tests, lint, typecheck, clean production build, and diff whitespace gates pass with results recorded in evidence.

## Rollback

Remove the router provider, route helpers/tests/recovery UI, restore the previous transient page navigation, and remove `react-router-dom` using npm. No backend, data, schema, or deployment rollback is required.

## Documentation and evidence updates

Update the source map, frontend test inventory, Phase 6 plan, project status, this task, and `docs/18-production-evidence/frontend-navigation-report.md` with observed results and explicit remaining UI-002 through UI-005 gaps.

## Completion evidence

Verified on 2026-07-14 with Node 24.14.0 and npm 11.9.0. The clean lock-stability gate preserved SHA-256 `6502B2385441EC553A52F41D2C37E91F7E782BDC77A7EB91290F457E7DBA5D09`; 23 targeted routing/application tests and all 27 frontend tests passed; lint and TypeScript passed; a clean environment-free Vite build transformed 92 modules; and a canonical source deep link returned the SPA shell with HTTP 200. Bundle and compatibility details are recorded in `docs/18-production-evidence/frontend-navigation-report.md`.
