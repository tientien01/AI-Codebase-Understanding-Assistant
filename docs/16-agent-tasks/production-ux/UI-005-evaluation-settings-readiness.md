---
id: UI-005
title: Replace evaluation and settings placeholders with truthful readiness UX
status: completed
priority: P0
phase: 6
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [UI-004, UI-002, EVA-002]
requirements:
  - docs/01-product/non-functional-requirements.md
  - docs/01-product/success-metrics.md
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
  - docs/10-ai-rag-and-evaluation/specifications/detailed-evaluation-plan.md
decisions: []
technology_docs:
  - docs/03-technology/stack-overview.md
  - docs/03-technology/technology-radar.md
allowed_paths:
  - .github/workflows/ci.yml
  - frontend/e2e/fixtures.ts
  - frontend/e2e/ui005.spec.ts
  - frontend/package.json
  - frontend/playwright.config.ts
  - frontend/src/AppRoutes.tsx
  - frontend/src/App.test.tsx
  - frontend/src/api/server.ts
  - frontend/src/components/common/AsyncState.tsx
  - frontend/src/features/server-state/asyncState.ts
  - frontend/src/features/server-state/index.ts
  - frontend/src/features/server-state/keys.ts
  - frontend/src/features/server-state/queries.ts
  - frontend/src/features/server-state/serverState.test.tsx
  - frontend/src/pages/workspace/EvaluationPage.tsx
  - frontend/src/pages/workspace/SettingsPage.tsx
  - frontend/src/pages/workspace/UI005Workspace.test.tsx
  - frontend/src/styles/components.css
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - docs/09-frontend-and-ux/README.md
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/15-plans/phases/phase-6-production-ux.md
  - docs/16-agent-tasks/production-ux/UI-005-evaluation-settings-readiness.md
  - docs/18-production-evidence/frontend-evaluation-settings-status-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/.env*
  - backend/app/api/**
  - backend/app/core/config.py
  - backend/app/db/**
  - backend/app/schemas/**
  - backend/app/services/**
  - evaluation/datasets/**
  - evaluation/gates/**
  - storage/**
dependency_changes:
  allowed: false
production_gates:
  - Settings renders only the existing authenticated `GET /api/v1/settings` and `GET /api/v1/settings/ignore-patterns` responses through TanStack Query; no secret value is requested, logged, cached in a URL, or rendered.
  - Evaluation does not invent benchmark questions, metrics, thresholds, run state, provider status, or success. Until the accepted evaluation endpoints exist, it renders a specific unavailable capability with the missing prerequisite and next action.
  - Repository/index readiness shown near Evaluation comes only from the selected repository and existing index-status query; repository lifecycle, job state, active index and provider configuration are not collapsed into a synthetic health score.
  - Loading, refreshing, stale, empty, limited, unavailable, permission-denied, retryable and terminal states remain distinguishable where applicable; retained data is visibly marked.
  - Settings is read-only in this slice. Missing `PATCH /settings/preferences` and `POST /settings/providers/test` APIs are disclosed; disabled controls cannot imply a successful mutation.
  - Canonical `/settings` and repository Evaluation routes, browser history, repository identity and current-index context remain owned by UI-001/UI-002 boundaries.
  - Keyboard, focus, landmarks, live-region behavior, text labels and reduced-motion behavior pass the declared browser checks with zero serious or critical axe findings.
  - Existing UI-001 through UI-004 behavior and CI remain green.
rollback:
  - Restore the prior Evaluation and Settings page components, UI-005 queries/types/tests and named CI job. No database, API, stored evaluation result, provider configuration or user preference rollback is required.
evidence_outputs:
  - docs/18-production-evidence/frontend-evaluation-settings-status-report.md
---

# UI-005 — Evaluation, settings, and readiness truthfulness

## Objective

Remove the remaining fabricated Evaluation and Settings content. Connect safe, non-secret Settings and ignore-pattern reads to the existing server-state boundary, present repository/index readiness without a synthetic score, and make the missing public Evaluation run capability explicitly unavailable rather than displaying invented benchmark questions or metrics.

## Verified starting point

- `SettingsPage.tsx` currently hard-codes indexing, parser, RAG, provider and danger-zone values, including generic “in development” language.
- `EvaluationPage.tsx` currently hard-codes four benchmark questions and empty metric labels even though no public evaluation endpoint is implemented.
- The backend already exposes authenticated `GET /api/v1/settings` and `GET /api/v1/settings/ignore-patterns` with non-secret effective values and configured booleans.
- The accepted API contract names evaluation datasets/runs/results and settings mutation/provider-test endpoints, but those routes are not present in the current OpenAPI baseline.
- UI-002 already owns repository and index-status server state. UI-004 supplies the Playwright/axe harness that this task extends.

## Scope

- Add typed frontend DTOs and API/query keys for the two existing Settings GET endpoints.
- Render effective indexing limits/profile, effective ignore patterns, provider names/models/configured booleans and security booleans from the server response. Translate machine keys into readable labels without changing their meaning.
- Show explicit configured/not configured and available/unavailable text; color is supplementary only.
- Extend the shared async projection only as needed for typed `limited` and `unavailable` states, preserving UI-002 retry/cancellation/stale rules.
- Replace Evaluation placeholder questions and dash metrics with:
  - current repository and active-index context from existing state;
  - an explicit unavailable Evaluation-run capability;
  - the exact missing accepted API families (`GET /evaluation/datasets`, `POST /evaluation/runs`, run status/results reads);
  - a safe next action explaining that offline CI evidence is not an interactive run result.
- Remove or relabel Settings controls whose backing mutation does not exist. No disabled action may look successful or imply that security invariants are configurable.
- Add focused component/query tests and deterministic Chromium journeys for Settings success/degraded states and Evaluation unavailable/readiness states.
- Add a named UI-005 browser/accessibility CI job or extend the existing frontend browser job with an independently reported UI-005 command.

## Non-goals

- Creating evaluation dataset/run/result APIs, persisting evaluation runs, executing providers, loading repository datasets in the browser, or turning checked-in CI evidence into an interactive run.
- Adding settings preference mutation, provider-test, credential entry, secret retrieval, deletion, re-index or restart APIs.
- Adding a new Status route or inventing a global health/readiness score.
- Changing backend schemas, routes, services, configuration, evaluation datasets/gates, database, storage, indexing, retrieval, assistant or graph behavior.
- Adding or upgrading dependencies.

## Implementation sequence

1. Add exact Settings/ignore-pattern DTOs, API methods, query keys and cancellable queries.
2. Extend async-state rendering for applicable limited/unavailable cases and cover it with tests.
3. Replace Settings placeholders with server-backed, non-secret read-only panels and honest unsupported-action disclosure.
4. Replace Evaluation placeholders with selected repository/index context plus the explicit missing-API unavailable state.
5. Add focused Vitest coverage and deterministic Playwright/axe journeys for success, permission, retry, stale/limited and unavailable behavior.
6. Run every declared gate, record observed route/browser/bundle behavior, update baseline/status/evidence and complete only after the named CI job passes.

## Required tests and commands

Use the locked frontend environment. Required commands:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd test -- --run src/pages/workspace/UI005Workspace.test.tsx src/features/server-state/serverState.test.tsx src/App.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e:ui005
Set-Location ..
git diff --check -- .github frontend docs
```

The focused tests must prove exact DTO/query ownership, non-secret rendering, readable configured booleans, unavailable evaluation language, repository/index context retention and applicable async-state recovery. Browser E2E must cover Settings success plus permission/retry behavior, Evaluation unavailable plus current repository/index disclosure, keyboard navigation and zero serious/critical axe findings. Full tests, lint, typecheck, clean build, unchanged lockfile, named CI and diff hygiene must pass.

## Acceptance criteria

- No hard-coded benchmark question, fake metric, generic success, generic “in development” value or synthetic health score remains on Evaluation or Settings.
- Settings values and effective ignore patterns come only from the existing authenticated API responses.
- Provider credential values are never requested or rendered; configured booleans and provider/model names remain distinguishable.
- Unsupported Settings mutations and interactive Evaluation runs are explicitly unavailable with their missing API prerequisite.
- Evaluation preserves selected repository and active-index context and never presents offline CI evidence as a user-triggered run.
- Applicable loading, refreshing, stale, limited, unavailable, permission, retryable and terminal states are accessible and actionable.
- Canonical routing, current UI-001 through UI-004 behavior, full frontend gates and the named UI-005 Playwright/axe job pass.
- Evidence records exact local/CI results, bundle observations and remaining API/release boundaries without claiming Phase 6 release completion.

## Documentation and evidence updates

Update the frontend UX README, implementation source/test inventories, Phase 6 plan, project status, this task and `docs/18-production-evidence/frontend-evaluation-settings-status-report.md`. UI-005 completion does not implement public evaluation runs, mutable settings, provider tests, accepted performance budgets or Phase 6 release qualification.

## Current verification state

Completed and verified on 2026-07-14. Clean install, 22 focused tests, all 51 frontend tests, lint, TypeScript, production build, four UI-005 Chromium journeys and all six UI-004 regression journeys pass. Settings success/permission/retry recovery, Evaluation repository/index context, keyboard reachability and zero serious/critical axe findings are verified; the package lock is unchanged. The named `Frontend UI-005 E2E and accessibility` GitHub Actions job passed for commit `2f22d77`. Exact observations, CI evidence and remaining API boundaries are recorded in `docs/18-production-evidence/frontend-evaluation-settings-status-report.md`.
