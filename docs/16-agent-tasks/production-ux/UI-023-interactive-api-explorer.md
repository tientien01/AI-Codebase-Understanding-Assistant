---
id: UI-023
title: Make API Explorer selectable, filterable, and source-linked
status: in_progress
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [UI-001, UI-002, UI-020]
requirements: [U019, U020]
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
  - docs/01-product/specifications/requirements-and-use-cases.md
allowed_paths:
  - backend/app/schemas/exploration.py
  - backend/app/services/repositories/repository_service.py
  - frontend/src/App.tsx
  - frontend/src/App.test.tsx
  - frontend/src/AppRoutes.tsx
  - frontend/src/api/server.ts
  - frontend/src/components/common/AsyncState.tsx
  - frontend/src/features/server-state/asyncState.ts
  - frontend/src/features/server-state/index.ts
  - frontend/src/features/server-state/keys.ts
  - frontend/src/features/server-state/queries.ts
  - frontend/src/features/server-state/serverState.test.tsx
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/ApiExplorerPage.tsx
  - frontend/src/pages/workspace/ApiExplorerPage.test.tsx
  - frontend/src/pages/workspace/SidePanels.tsx
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - frontend/src/utils/apiEndpoint.ts
  - tests/test_codebase_service.py
  - docs/15-plans/task-register.md
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
  - docs/16-agent-tasks/production-ux/UI-023-interactive-api-explorer.md
  - docs/18-production-evidence/api-explorer-interaction-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - frontend/package.json
  - frontend/package-lock.json
dependency_changes:
  allowed: false
production_gates:
  - Endpoint filters and selection are real controls with keyboard-accessible state.
  - Selected endpoint identity survives reload and browser navigation through the canonical API route.
  - Endpoint detail opens the exact indexed source range and can launch a bounded API-flow projection.
  - Generic query cache eligibility is not presented as stale repository data.
  - Backend focused tests and frontend tests, lint, typecheck, and production build pass.
evidence_outputs:
  - docs/18-production-evidence/api-explorer-interaction-report.md
---

# Task UI-023 — Interactive API Explorer

## Context

The API Explorer renders endpoint facts but its method chips, rows, and detail panel are disconnected. The detail always shows the first endpoint, the canonical `endpoint` route parameter is ignored, and normal query cache expiry is presented as a global "Cached data" warning.

## Objective

Deliver an evidence-backed API browsing workflow from endpoint discovery through stable selection, source inspection, and bounded request-flow exploration.

## In scope

- Add a stable endpoint key to the existing endpoint read model.
- Regenerate the committed OpenAPI artifact without weakening its drift gate.
- Load API endpoints through the owned endpoint-list query.
- Add text and method filters, selected-row state, URL persistence, and useful empty results.
- Bind API Detail to the selected endpoint with source and API-flow actions.
- Stop treating generic TanStack Query cache eligibility as user-visible stale repository data.
- Add focused backend/frontend regressions and production evidence.

## Out of scope

- Auth, request schema, or response schema inference not already supported by deterministic parser evidence.
- Graph algorithm, parser, queue, indexing, or persistence redesign.
- New dependencies or endpoint pagination policy.

## Existing code to reuse

- Canonical API route query support in `frontend/src/routing/routes.ts`.
- Endpoint-list route under `/repositories/{repository_id}/api/endpoints`.
- Code Explorer source navigation and API-flow graph projection.
- TanStack Query version-scoped keys and async state projection.

## Implementation sequence

1. Expose deterministic endpoint identity and consume the endpoint-list API.
2. Connect filters, selection, deep link, detail, source, and flow actions.
3. Correct generic cache-state presentation.
4. Add regressions, evidence, and run all declared gates.

## Data/API compatibility and migration

`endpoint_key` is an additive response field derived deterministically from existing endpoint facts. No database or migration change is required. The deterministic OpenAPI export also records projection-limit drift already present in the server source so CI compares against the actual current contract.

## Failure, security, performance, and observability requirements

- Never infer auth or schemas when parser evidence is absent.
- Preserve repository-relative source paths and existing route safety checks.
- Filtering remains bounded to the currently returned endpoint list.
- Missing or stale endpoint keys recover with an explicit no-selection detail state.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/test_codebase_service.py -q
Set-Location frontend
npm.cmd test -- --run src/pages/workspace/ApiExplorerPage.test.tsx src/features/server-state/serverState.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check
```

## Acceptance criteria

- Search and method filters change the visible endpoint set and expose a filter-specific empty state.
- Selecting a row updates API Detail and `?endpoint=`; a valid deep link restores selection.
- Source and request-flow actions retain repository and endpoint context.
- Unsupported auth/schema information is not represented as an interactive filter or asserted fact.
- Query `isStale` alone does not create a global "Cached data" banner.
- All required verification passes and is recorded in the evidence report.

## Rollback

Remove the additive endpoint key and restore Overview-backed endpoint rendering; no stored data rollback is needed.

## Documentation and evidence updates

- Add UI-023 to the task register.
- Record commands and outcomes in the API Explorer interaction evidence report.
