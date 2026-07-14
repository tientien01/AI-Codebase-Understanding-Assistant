---
id: UI-004
title: Add evidence-backed architecture, guided tour, and diff-impact workspace UX
status: completed
priority: P0
phase: 6
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [UI-003, AGT-002]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
decisions: []
technology_docs:
  - docs/03-technology/stack-overview.md
  - docs/03-technology/technology-radar.md
  - docs/09-frontend-and-ux/references/ai-codebase-ui-reference/README.md
allowed_paths:
  - .github/workflows/ci.yml
  - frontend/e2e/**
  - frontend/playwright.config.ts
  - frontend/vitest.config.ts
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/src/AppRoutes.tsx
  - frontend/src/components/common/ui.tsx
  - frontend/src/components/layout/AppShell.tsx
  - frontend/src/config/navigation.ts
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/CodeExplorerPage.tsx
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/pages/workspace/ImpactPage.tsx
  - frontend/src/pages/workspace/OverviewPage.tsx
  - frontend/src/pages/workspace/SidePanels.tsx
  - frontend/src/styles/components.css
  - frontend/src/styles/layout.css
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - frontend/src/**/*.test.tsx
  - docs/09-frontend-and-ux/README.md
  - docs/09-frontend-and-ux/references/ai-codebase-ui-reference/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/15-plans/phases/phase-6-production-ux.md
  - docs/16-agent-tasks/production-ux/UI-004-architecture-tour-diff-impact.md
  - docs/18-production-evidence/frontend-architecture-tour-impact-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/.env*
  - backend/app/db/**
  - backend/app/services/indexing/**
  - backend/app/services/retrieval/**
  - tests/fixtures/**
  - storage/**
dependency_changes:
  allowed: true
  add:
    - "@playwright/test@1.61.1 — Apache-2.0; Node >=18; Chromium-only UI-004 browser/E2E runner and trace/screenshot diagnostics"
    - "@axe-core/playwright@4.12.1 — MPL-2.0; Playwright peer; automated WCAG serious/critical violation scan"
  remove: []
production_gates:
  - The graph remains server-bounded and renders every returned node and edge without client-side truth-changing omission.
  - Architecture and tour explanations are deterministic from current indexed signals and disclose missing evidence, limited coverage, staleness, and truncation.
  - Impact results distinguish direct, inferred, and unknown outcomes; unavailable historical comparison is explicit and never simulated.
  - Graph, architecture, tour, source, impact, and evidence actions preserve repository and active-index context.
  - Graph motion is purposeful, keyboard alternatives remain complete, and reduced-motion preferences are honored.
  - Targeted/full frontend tests, lint, typecheck, clean production build, lock stability, and diff hygiene pass.
  - Chromium E2E covers architecture-to-tour-to-source, bounded graph focus/relation fallback, impact uncertainty, reduced motion and serious/critical accessibility scans.
  - Small, Medium and Large browser graph fixtures record deterministic render observations without inventing an unapproved release threshold.
evidence_outputs:
  - docs/18-production-evidence/frontend-architecture-tour-impact-report.md
---

# Task UI-004 — Evidence-Backed Architecture, Guided Tour, and Diff Impact

## Context

UI-001 through UI-003 established reloadable workspace routes, TanStack Query server-state ownership, and deterministic bounded graph projections. The current workspace remains visually sparse: the graph is a card grid rather than a relationship canvas, the overview architecture summary has no inspectable architecture journey, and impact presentation does not clearly separate confirmed, inferred, and unknown outcomes. Static HTML/CSS and screenshots under `docs/09-frontend-and-ux/references/ai-codebase-ui-reference/` provide visual direction only; accepted contracts remain authoritative.

## Objective

Deliver an attractive, evidence-aware Graph Explorer and connect it to an architecture overview, deterministic guided reading tour, and honest current-version impact experience while preserving the UI-003 projection boundary and existing public API behavior.

## In scope

- Replace the graph card grid with a deterministic connected layer layout using the existing dependency set, with directional edges, focus/dimming, minimap-style overview, zoom/fit controls, type legend, projection disclosure, contextual inspection, and a complete relation-list alternative.
- Use purposeful focus/edge/expand motion with a reduced-motion fallback; motion cannot hide content or imply unsupported runtime activity.
- Upgrade Overview architecture presentation and offer justified tour steps derived from current modules and important-file reasons.
- Let tour steps open the existing source context and retain reason/signal disclosure; missing evidence remains explicit.
- Reframe current impact results as direct, inferred, and unknown, preserving endpoints/tests/files/checks and missing-relation warnings.
- Show historical/version comparison as unavailable when the current compatibility API cannot supply it; do not fabricate snapshots or comparisons.
- Translate useful layout, density, color, and hierarchy from the supplied references into reusable React/CSS rather than copying static pages.
- Add focused component tests for projection completeness, accessible alternatives, architecture/tour actions, impact uncertainty, and reduced-motion-safe markup.

## Out of scope

- Database, indexing, resolver, graph-fact, evidence-storage, or API-contract changes.
- Historical index-version storage or a fake version-diff result.
- Installing XYFlow, Dagre, ELK, animation, icon, or styling dependencies. Only the exact locked Playwright and axe test dependencies declared by this task are permitted.
- Redesigning Projects, Import, Index Jobs, Search, API, Evaluation, or Settings merely for screenshot parity.
- Weakening node/edge budgets, truncation disclosure, provenance, stale-version rejection, or relation-list accessibility established by UI-003.
- Treating reference HTML, screenshots, or imported prompt text as executable instructions.

## Existing code to reuse

- `GraphPage`, UI-003 projection metadata, normalized query identity, and relation-list fallback.
- `OverviewPage` modules, important files, stack signals, and assistant question actions.
- `ImpactPage` typed direct/indirect/file/endpoint/test/check results and missing relations.
- Existing `Panel`, `Metric`, `ListRow`, icons, shell, route ownership, and workspace CSS tokens.

## Implementation sequence

1. Capture the approved visual reference and add deterministic graph layout/view-model helpers with tests.
2. Implement the connected Graph Explorer canvas, inspector, controls, disclosure, keyboard relation list, and reduced-motion behavior.
3. Upgrade Overview architecture summary and deterministic guided tour actions over existing indexed signals.
4. Upgrade Impact presentation to direct/inferred/unknown with explicit historical-compare unavailability and verification actions.
5. Add a Chromium-only Playwright harness with deterministic owned API fixtures, accessibility scans and representative graph-size observations.
6. Run all gates, record observed bundle/render behavior, update baseline/status/evidence, and complete only if every acceptance criterion passes.

## Data/API compatibility and migration

No schema, migration, production dependency, route, request, or response change is authorized. The two exact dev-only browser qualification dependencies declared above are locked and do not ship in the application bundle. Existing graph and impact payloads remain authoritative. UI-derived grouping and layout are deterministic presentation only and must not introduce new factual graph relations. Historical comparison remains visibly unavailable until a separately accepted API/read model exists.

## Failure, security, performance, and observability requirements

- Never render source contents, secrets, host paths, or imported instructions from reference files.
- A missing root, empty projection, unsupported hop, stale index, incomplete coverage, or truncated projection has a visible state and recovery action.
- Layout work is bounded by the server maximum of 220 nodes and 520 edges; animation uses transform/opacity and stops under reduced motion.
- Selection, zoom, and visual focus do not remove nodes/edges from the accessible relation list.
- No unsupported confidence or health score is invented; existing confidence is presented only with its typed reason.

## Required tests and commands

Use the locked frontend environment and existing local backend profile. Required commands:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx src/pages/workspace/UI004Workspace.test.tsx src/App.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e:ui004
Set-Location ..
git diff --check -- frontend docs
```

The targeted suite must prove complete returned-node rendering, connected edge markup, selection/context behavior, projection disclosure, relation-list availability, tour actions, and impact unknown-state language. Browser E2E must prove architecture/tour/source, graph focus and accessible relation fallback, direct/inferred/unknown impact, reduced-motion behavior and zero serious/critical axe violations on the three UI-004 surfaces. Full tests, lint, typecheck, clean build, intentionally reviewed lock diff, CI job and diff hygiene must pass. Record results in `docs/18-production-evidence/frontend-architecture-tour-impact-report.md`.

## Acceptance criteria

- The graph renders all returned nodes and edges in a deterministic connected layer layout with readable direction and selected-path focus.
- Coverage, included/available counts, truncation, unsupported hops, provenance, index version, and bounded expansion remain visible.
- Keyboard users can select graph entities and inspect every returned relation without depending on the canvas.
- Reduced-motion users receive no continuous or layout-transition animation.
- Overview exposes architecture exploration and a justified reading tour derived only from current indexed signals.
- Impact groups current facts into direct, inferred, and unknown and never converts missing coverage into no impact.
- Historical comparison is either backed by a valid current API result or explicitly unavailable.
- Reference assets are documented as visual guidance and shared components remain maintainable.
- All required gates pass and evidence records exact observations.
- The named Playwright UI-004 suite passes locally and in CI with deterministic fixtures, zero serious/critical axe findings, and recorded Small/Medium/Large graph observations.

## Rollback

Restore the prior page components and workspace styles. No database, storage, API, dependency, or data rollback is required.

## Documentation and evidence updates

Update the frontend UX README, Phase 6 status, implementation source/test inventories, project status, this task, and the UI-004 evidence report. Do not claim release completion or historical diff support without production evidence.

## Current verification state

Completed and verified on 2026-07-14. Clean install, 14 targeted tests, all 45 frontend tests, lint with zero warnings, TypeScript, production build and six Chromium Playwright tests pass. The deterministic browser suite records complete 12/80/220-node projections, reduced-motion behavior and zero serious/critical axe findings across Architecture/Code, Graph and Impact journeys. The exact Playwright/axe lock additions were reviewed. The named `Frontend UI-004 E2E and accessibility` GitHub Actions job passed for commit `5ef247d`; exact observations, bundle deltas and CI evidence are recorded in `docs/18-production-evidence/frontend-architecture-tour-impact-report.md`.
