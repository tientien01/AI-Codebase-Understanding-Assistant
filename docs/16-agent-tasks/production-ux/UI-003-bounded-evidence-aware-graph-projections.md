---
id: UI-003
title: Add bounded evidence-aware graph projections
status: in_progress
priority: P0
phase: 6
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [INT-004, UI-002]
requirements: []
contracts:
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
decisions: []
technology_docs:
  - docs/03-technology/stack-overview.md
  - docs/03-technology/technology-radar.md
allowed_paths:
  - backend/app/api/v1/routes/graph.py
  - backend/app/schemas/graph.py
  - backend/app/services/application/use_cases.py
  - backend/app/services/codebase_service.py
  - backend/app/services/graph/graph_service.py
  - backend/app/services/graph/graph_projection_service.py
  - frontend/src/AppRoutes.tsx
  - frontend/src/api/server.ts
  - frontend/src/features/server-state/keys.ts
  - frontend/src/features/server-state/queries.ts
  - frontend/src/features/server-state/serverState.test.tsx
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/pages/workspace/SidePanels.tsx
  - frontend/src/styles/pages/workspace.css
  - frontend/src/styles/components.css
  - frontend/src/types/api.ts
  - tests/test_graph_projection.py
  - tests/test_api_contract.py
  - docs/14-implementation-baseline/api-coverage.md
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/15-plans/phases/phase-6-production-ux.md
  - docs/16-agent-tasks/production-ux/UI-003-bounded-evidence-aware-graph-projections.md
  - docs/18-production-evidence/frontend-graph-projection-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/db/**
  - backend/app/services/indexing/**
  - backend/app/services/retrieval/**
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/src/routing/**
  - tests/fixtures/**
  - storage/**
dependency_changes:
  allowed: false
production_gates:
  - Graph requests declare deterministic server-enforced node/edge budgets and supported projection filters.
  - Graph responses disclose available/included counts, coverage, truncation reason, unsupported hops, expansion affordance and provenance without silently slicing on the client.
  - Repository/index/view/projection query identities cannot collide, and expansion preserves scoped invalidation.
  - The graph surface exposes bounded controls, visible limited states and a keyboard-accessible relation-list fallback.
  - Existing graph endpoints and response fields remain backward compatible.
  - Backend targeted/full local-profile tests and frontend targeted/full/lint/typecheck/clean-build gates pass.
evidence_outputs:
  - docs/18-production-evidence/frontend-graph-projection-report.md
---

# Task UI-003 — Bounded Evidence-Aware Graph Projections

## Context

The current graph service returns unbounded compatibility DTO lists while `GraphPage` silently slices them to 18 nodes and 8 edges. The UI therefore cannot distinguish a complete projection from an arbitrary client subset, and requests do not declare root/type/direction/depth or size bounds required by the accepted graph and REST contracts.

## Objective

Serve deterministic, server-bounded graph projections that disclose coverage, truncation and provenance, then render the full returned projection with accessible controls and relation-list fallback while preserving current endpoint paths and UI-001/UI-002 ownership.

## In scope

- Add typed projection query inputs for roots, node/edge types, direction, depth, confidence/support filters and client node/edge bounds capped by server policy.
- Extend graph responses with repository/index/view identity, available/included counts, coverage, truncation, unsupported hops, continuation/expand affordance and projection provenance.
- Apply deterministic filtering, bounded traversal and stable node/edge ordering in the existing graph projection service.
- Preserve current view-specific endpoints and legacy `nodes`/`edges` fields.
- Include projection inputs in TanStack Query keys and forward them to the API.
- Remove client-side node/edge slicing; add bounded controls, explicit limited/complete disclosure and a keyboard-accessible relation list.
- Add deterministic correctness, compatibility, large synthetic graph and frontend interaction tests.
- Record observed behavior and performance without inventing a release threshold.

## Out of scope

- Canonical graph storage/schema changes, new parser/resolver/indexing composition or database migrations.
- Cross-file resolution, CFG/DFG generation or graph correctness claims beyond current indexed data.
- Architecture/tour/diff impact UX (`UI-004`) and evaluation/settings/status surfaces (`UI-005`).
- Installing XYFlow, Dagre, ELK, Graphology, Web Workers, Playwright or MSW without a separate accepted benchmark/decision.
- Authentication, authorization, pagination tokens with persisted server state or unrestricted graph export.

## Compatibility and safety

Existing routes and `nodes`/`edges` remain available. New response metadata is additive. Client bounds may only reduce fixed server maxima. Stable ordering and owner/version identity prevent cache collisions and cross-repository fallback. Source paths/provenance use existing safe DTO fields; no source contents, secrets or imported instructions are emitted.

## Required verification

Use the existing project `.venv` and locked frontend environment. Run targeted graph/API Pytest, the required local-profile backend suite, frontend targeted/full tests, lint, typecheck, lock stability and a clean production build. Large synthetic projection evidence must report observed size/time without creating an unapproved pass threshold.

## Acceptance criteria

- The server, not the client, enforces deterministic maximum nodes/edges and reports whether/why a result is truncated.
- Root/type/direction/depth/confidence/support filters are validated and represented in response provenance.
- Every returned edge references included nodes; counts and coverage are internally consistent.
- Graph query keys include repository, active index version, view and normalized projection input.
- The graph page renders every returned node/edge, labels complete versus limited coverage, offers bounded expansion and retains an accessible relation list.
- Existing callers that omit projection parameters still receive a valid bounded response.
- All required local gates and documentation/evidence updates pass.

## Rollback

Restore legacy graph responses and frontend query signature, then restore the client visualization. No schema, data or dependency rollback is required.
