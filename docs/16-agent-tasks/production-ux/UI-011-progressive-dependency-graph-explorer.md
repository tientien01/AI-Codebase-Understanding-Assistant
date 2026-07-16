---
id: UI-011
title: Add adaptive progressive dependency graph exploration
status: in_progress
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-003, UI-010, INT-003]
requirements: []
contracts:
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
decisions: []
technology_docs:
  - docs/03-technology/stack-overview.md
  - docs/03-technology/technology-radar.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/api/v1/routes/graph.py
  - backend/app/schemas/graph.py
  - backend/app/services/application/use_cases.py
  - backend/app/services/codebase_service.py
  - backend/app/services/graph/graph_projection_service.py
  - frontend/src/api/server.ts
  - frontend/src/AppRoutes.tsx
  - frontend/src/features/server-state/keys.ts
  - frontend/src/features/server-state/queries.ts
  - frontend/src/features/server-state/serverState.test.tsx
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - frontend/e2e/**
  - tests/test_graph_projection.py
  - tests/test_api_contract.py
  - tests/test_code_analysis.py
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/production-ux/UI-011-progressive-dependency-graph-explorer.md
  - docs/18-production-evidence/progressive-dependency-graph-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/app/services/indexing/**
  - backend/app/services/parsing/**
  - backend/app/services/code_analysis/**
  - backend/app/services/retrieval/**
  - backend/migrations/**
  - frontend/package.json
  - frontend/package-lock.json
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Initial dependency seeds are deterministic, adaptive to repository evidence, diverse across graph regions, reason-labelled and never padded to a fixed count.
  - Progressive expansion requests one bounded hop from an explicit node and direction, merges without duplicate nodes or edges, preserves already-visible positions and discloses leaf, limited and continuation states.
  - Resolved internal imports and detected module imports remain visibly distinct; compatibility data is not upgraded into canonical or external-package truth.
  - The graph canvas owns the majority of the workspace while onboarding, filters, status, inspector and accessibility alternatives remain available in compact or on-demand form.
  - Existing server maxima, repository/index ownership, deterministic ordering, coverage, truncation, provenance and no-dangling-edge invariants remain enforced.
  - No LLM, new dependency, parser/resolver, persistence, migration or graph-producer change is introduced.
  - Targeted/full backend and frontend gates, OpenAPI drift, lint, typecheck, production build and UI-004 Chromium graph accessibility regression pass.
evidence_outputs:
  - docs/18-production-evidence/progressive-dependency-graph-report.md
---

# Task UI-011 — Adaptive Progressive Dependency Graph Explorer

## Context

The current Dependencies surface requests a broad bounded projection, asks users to select a node count and depth up front, and rebuilds one complete layer layout whenever the result changes. It does not provide adaptive starting points, per-node expansion state or stable branch-by-branch exploration. The large explanatory and filter controls also reduce the graph canvas even after the user understands the view.

The project owner authorized this task on 2026-07-15. Completed UI-003/UI-010 behavior remains the compatibility and UX baseline, while the accepted graph and workspace contracts remain authoritative.

## Objective

Deliver an evidence-aware Dependencies workspace that starts from a deterministic adaptive set of suggested starting points and lets users expand one bounded branch at a time, while making the graph the dominant workspace surface and retaining honest coverage and accessible alternatives.

## In scope

- Additive dependency seed and per-node expansion metadata on the existing compatibility graph response.
- Deterministic dependency seed ranking from existing node roles, confirmed topology, coverage and graph-region diversity, with repository-relative stopping and explicit reason codes.
- Separate resolved internal file relations from detected file-to-module imports without claiming unresolved modules are external packages.
- One-hop incoming, outgoing or both expansion with continuation/remaining disclosure and existing server maxima.
- Frontend accumulated graph state, deterministic node/edge deduplication, stable positions for already-visible nodes, focused-path highlighting, unrelated-branch dimming, leaf/limited states and branch reset/collapse controls.
- A compact graph-first toolbar, search/focus affordance, relationship controls, on-demand help/advanced filters, compact status and collapsible inspector/relation alternative.
- Backward-compatible behavior for non-progressive graph views and callers that omit the new inputs.
- Focused backend, frontend and Chromium accessibility/regression coverage.

## Out of scope

- Parser, resolver, graph-candidate producer, canonical graph persistence, database or migration changes.
- Declared manifest/package dependencies, cross-language internal resolution parity, new external-package classification, cycle-analysis claims or historical graph comparison.
- LLM-selected seeds, inferred architectural importance, unrestricted graph loading or silent client-side omission.
- New graph/layout dependencies, Web Workers or replacement of the existing renderer without a separately accepted benchmark/technology decision.

## Existing code to reuse

- `GraphProjectionService` filtering, traversal, ordering, budgets and coverage/truncation response.
- Existing `imports` and `imports_internal` compatibility relations without changing their producers.
- TanStack Query repository/index/view/projection identities and cancellation.
- `GraphPage` SVG/HTML renderer, relation-list fallback, zoom/minimap, inspector and reduced-motion styles.

## Implementation sequence

1. Characterize current dependency projection and add typed additive seed/expansion contracts.
2. Implement deterministic adaptive seed selection, dependency scopes and one-hop expansion metadata with backend tests.
3. Add normalized frontend query inputs and accumulated expansion state with deterministic merge tests.
4. Convert Dependencies to graph-first progressive interaction while preserving other graph views.
5. Update Chromium fixtures/regressions, OpenAPI, baseline and exact evidence.

## Data/API compatibility and migration

No migration or persistence change. Existing GET graph endpoints, request defaults and `nodes`/`edges` fields remain valid. New request fields are optional and new response fields are additive. Progressive state is repository/index/view scoped and must be discarded on owner, active-version, view or dependency-scope change. Compatibility `imports_internal` remains explicitly non-canonical and is not renamed or persisted by this task.

## Failure, security, performance, and observability requirements

- All seed and expansion work is deterministic, bounded and independent of imported code execution, providers and LLM output.
- Expansion never crosses repository or active-index ownership and never accepts host paths.
- Missing roots, unsupported internal resolution, exhausted branches, truncation and continuation are distinct safe states.
- Existing node/edge hard maxima remain authoritative; frontend merge stops visibly at the declared workspace budget rather than silently dropping facts.
- Browser observations record Small/Medium/Large behavior without inventing an unapproved release threshold.

## Required tests and commands

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest ..\tests\test_graph_projection.py ..\tests\test_api_contract.py ..\tests\test_code_analysis.py -q
.\.venv\Scripts\python.exe -m pytest ..\tests -q
.\.venv\Scripts\python.exe scripts\export_openapi.py --check
Set-Location ..\frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx src/features/server-state/serverState.test.tsx src/App.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
npm.cmd run test:e2e:ui004
Set-Location ..
git diff --check -- backend frontend tests docs
```

## Acceptance criteria

- A repository with fewer qualifying starting points displays only those points; a repository with many candidates stops by deterministic marginal value/diversity and discloses additional candidates.
- Every suggested starting point has stable reason codes derived from indexed facts, not an opaque score or LLM classification.
- Clicking an expandable dependency node adds only its requested bounded one-hop delta, keeps existing nodes stable, avoids duplicates and exposes remaining/continuation state.
- Selecting a deeper node highlights its active branch and dims unrelated branches without deleting them or changing graph truth.
- Internal file relations and detected module imports have distinct labels, node vocabularies and empty/limited language.
- Projection-size, raw node-type and raw relation-type controls no longer occupy the primary Dependencies workspace; equivalent diagnostics remain available on demand.
- The canvas occupies the majority of the usable graph page, with keyboard-accessible expansion, inspection, reset and complete relation-list behavior.
- All declared gates pass and exact results are recorded in the evidence report.

## Rollback

Restore the UI-010 single-projection Dependencies behavior and remove the additive seed/expansion request and response fields. Existing graph DTOs, producers and stored repository state require no rollback.

## Documentation and evidence updates

Record the algorithm, compatibility boundaries, exact commands, test counts, browser observations, bundle output and remaining canonical/multi-language limitations in `docs/18-production-evidence/progressive-dependency-graph-report.md`. Do not mark this task complete until every required gate passes.
