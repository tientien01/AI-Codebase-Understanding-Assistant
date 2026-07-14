---
id: UI-010
title: Make Graph Explorer focus-first and self-explanatory
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-004]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
  - docs/05-domain-contracts/parsing-and-graph.md
allowed_paths:
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/styles/pages/workspace.css
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/production-ux/UI-010-guided-graph-explorer.md
  - docs/18-production-evidence/guided-graph-explorer-report.md
forbidden_paths:
  - backend/.env*
  - backend/app/**
  - frontend/package.json
  - frontend/package-lock.json
dependency_changes:
  allowed: false
production_gates:
  - Existing server-bounded projections, counts, provenance, coverage and truncation remain authoritative.
  - Architecture overview is not duplicated as an unexplained full-repository graph.
  - Every visible graph mode states its user question, permitted node meaning and edge meaning.
  - Detail projections require or invite a human-readable focus and explain empty or unsupported relations.
  - Initial graph rendering does not dim unrelated nodes before an explicit user selection.
  - The complete keyboard-accessible relation list remains available without dominating the default visual layout.
  - Targeted/full frontend tests, lint, typecheck, production build and diff hygiene pass locally.
evidence_outputs:
  - docs/18-production-evidence/guided-graph-explorer-report.md
---

# Task UI-010 — Guided Graph Explorer

## Context

The current Graph Explorer exposes Architecture, Dependencies, API Flow, Function Flow and Data Flow as unexplained peer tabs. Users cannot tell what a node represents, why arrows appear or disappear, or which projection answers their question. The default projection also selects the first node and dims most of the canvas before the user acts.

## Objective

Turn Graph Explorer into a focus-first relationship workspace that explains the purpose, node vocabulary, edge semantics, scope and degraded states of each projection without changing graph truth or API behavior.

## In scope

- Replace the duplicate Architecture tab experience with a guided relationship chooser.
- Present Dependencies, Request Flow and Call Flow as primary user questions; keep Value Flow visibly advanced.
- Add view-specific descriptions, focus selection, projection summaries, node/edge legends and honest empty guidance.
- Limit visual ambiguity through view-specific node presentation and explicit relation verbs.
- Remove implicit initial dimming, keep selection clearing available and retain bounded expansion.
- Compact projection controls and keep the accessible relation list collapsed by default.
- Improve graph viewport/inspector layout and dark-theme action consistency.
- Clear incompatible root focus when switching relationship views while preserving the chosen depth.
- Add focused regression tests and local verification evidence.

## Out of scope

- Backend projection, indexer, resolver, CFG/DFG, API or schema changes.
- Inventing request sequence, reads/writes/returns relations or capability readiness absent from the response.
- Replacing the existing deterministic layout engine or adding a graph dependency.
- Redesigning Overview or other workspace pages.

## Required tests and commands

```powershell
Set-Location frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- frontend docs
```

## Acceptance criteria

- A first-time user can choose a relationship question without interpreting raw graph terminology.
- Dependencies explains file/module import nodes and import direction.
- Request Flow explains endpoint/call nodes and only claims returned relation types.
- Call Flow explains callable nodes; Value Flow is labeled advanced and compiler-level.
- The current focus, direction, depth, included counts and relation meaning remain visible.
- No-edge states distinguish a valid empty result from limited or unresolved evidence.
- Initial nodes remain fully visible until the user explicitly selects one.
- Projection controls, inspector and accessible relation list remain keyboard usable.

## Documentation and evidence updates

Record exact local command results in `docs/18-production-evidence/guided-graph-explorer-report.md`. Mark this task completed only after every required local gate passes. CI is intentionally not checked for this owner-requested delivery.

## Current verification state

Completed and locally verified on 2026-07-15 after rebasing onto the main branch that includes UI-009. The targeted GraphPage suite passes 7 tests, the full frontend suite passes 66 tests across 13 files, ESLint and TypeScript pass, the Vite production build succeeds with 145 transformed modules, and frontend/docs diff hygiene passes. CI was intentionally not checked at the project owner's request.
