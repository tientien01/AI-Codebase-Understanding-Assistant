---
id: UI-008
title: Deliver a sixty-second architecture map and evidence-rich assistant drawer
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-004, UI-007]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/schemas/exploration.py
  - backend/app/services/repositories/repository_service.py
  - frontend/src/AppRoutes.tsx
  - frontend/src/components/chat/AssistantChat.tsx
  - frontend/src/components/common/Icon.tsx
  - frontend/src/components/layout/AppShell.tsx
  - frontend/src/features/server-state/queries.ts
  - frontend/src/pages/workspace/OverviewPage.tsx
  - frontend/src/pages/workspace/WorkspaceLayout.tsx
  - frontend/src/pages/workspace/UI008Architecture.test.tsx
  - frontend/src/pages/workspace/UI007Overview.test.tsx
  - frontend/src/styles/layout.css
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - tests/test_codebase_service.py
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
  - docs/16-agent-tasks/production-ux/UI-008-sixty-second-architecture-assistant.md
  - docs/18-production-evidence/sixty-second-architecture-assistant-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/migrations/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Overview exposes a deterministic repository-specific architecture summary rather than raw alphabetical folders or a universal fixed layer list.
  - Every displayed relationship and primary-flow step retains typed support and source-derived evidence; missing support remains unknown.
  - The sixty-second view identifies system purpose, technologies, major areas, primary flows, infrastructure, and a justified reading start without diagnostic clutter.
  - Overview-to-Graph and Overview-to-source actions preserve repository context.
  - The assistant drawer provides accessible history/new-chat affordances, contextual suggestions, evidence disclosure, trace summary, multiline composer, and a real collapsed rail.
  - Backend and frontend required gates pass without dependency changes.
evidence_outputs:
  - docs/18-production-evidence/sixty-second-architecture-assistant-report.md
---

# Task UI-008 — Sixty-second architecture and assistant

## Context

The owner accepted a C4-lite architecture direction after reviewing UI-007 in the running application. UI-007 improved density but still exposes directory-derived module cards, no supported connections, and the legacy chat body inside a drawer shell. The owner requires a newcomer to answer “what is this repository and how do its major parts work together?” in sixty seconds.

## Objective

Produce a bounded deterministic architecture read model and render it as a compact system/component map with supported connections and primary flows, while completing the IDE-style assistant drawer experience.

## In scope

- Extend the Overview response with typed architecture areas, relationships, technologies, external/infrastructure signals, primary flows, evidence/support labels, summary, and coverage disclosure.
- Derive only deterministic facts from indexed files, endpoints, symbols, graph nodes/edges, and known technology markers; do not use optional provider prose as fact.
- Render a C4-lite container/component overview with labelled confirmed/inferred lines and graph/source actions.
- Replace raw Key Modules with justified Key Areas and add compact primary flows.
- Complete the assistant drawer header, empty-state prompts, evidence accordion, trace summary, multiline composer, and collapsed rail using the current conversation contract.
- Add semantic icons using the existing locked icon dependency.

## Out of scope

- LLM-authored architecture facts, new dependencies, migrations, persistence, graph producer changes, or unbounded graph queries.
- Claiming runtime deployment topology, databases, caches, vector stores, or external providers without indexed evidence.
- Redesigning Graph Explorer or unrelated management pages.

## Existing code to reuse

- Current Overview DTO/service, repository graph nodes/edges, important-file reasons, endpoint metadata, UI-004 graph navigation, UI-007 compact layout, AssistantChat, citation actions, and Lucide icon dependency.

## Implementation sequence

1. Add backend architecture DTOs and focused service tests for a representative layered repository and insufficient evidence.
2. Build deterministic bounded architecture areas, relations and flows from current repository facts.
3. Update the OpenAPI contract and frontend types.
4. Render the sixty-second architecture map, primary flows, key areas, reading actions and semantic icons.
5. Complete assistant drawer interactions and component tests.
6. Run all declared gates and record exact evidence.

## Data/API compatibility and migration

Overview gains additive response fields. Existing fields remain for compatibility; there is no request, route, persistence, migration, or dependency change.

## Failure, security, performance, and observability requirements

- Imported repository text is data, never instructions; architecture summaries use bounded deterministic templates.
- No source contents, secrets, host paths, or unsupported infrastructure claims are exposed.
- Returned architecture collections are bounded and deterministically ordered.
- Support uses `confirmed`, `inferred`, or `unknown`; inferred is never styled as confirmed.
- Keyboard, focus, expanded state, text alternatives, responsive layout, and reduced-motion behavior remain usable.

## Required tests and commands

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest ..\tests\test_codebase_service.py -q
.\.venv\Scripts\python.exe -m pytest ..\tests\test_service_boundaries.py ..\tests\test_api_contract.py -q
.\.venv\Scripts\python.exe scripts\export_openapi.py --check
Set-Location ..\frontend
npm.cmd test -- --run src/pages/workspace/UI008Architecture.test.tsx src/pages/workspace/UI007Overview.test.tsx src/pages/workspace/UI004Workspace.test.tsx src/App.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- backend frontend tests docs
```

## Acceptance criteria

- A representative full-stack repository returns and displays presentation, backend components, data/infrastructure signals, supported relations and at least one primary flow when facts exist.
- A repository without sufficient evidence receives an explicit limited architecture result without invented layers or edges.
- Architecture relationships are labelled, directional, support-aware, bounded, and traceable to indexed facts.
- Overview no longer presents raw folders as the architecture mental model or repeats the same data in Key Areas.
- The assistant has no nested legacy welcome card, exposes evidence/trace sections when available, uses a multiline composer, and collapses to a narrow rail.
- Targeted/full backend and frontend gates, OpenAPI drift, lint, typecheck, build and diff hygiene pass.

## Rollback

Remove additive architecture response fields and restore the UI-007 signal-card Overview and drawer body. No data rollback is required.

## Documentation and evidence updates

Update the REST contract, OpenAPI artifact, this task and the evidence report with exact results and remaining evidence limits.

Completed on 2026-07-15. Exact verification results and evidence limits are recorded in `docs/18-production-evidence/sixty-second-architecture-assistant-report.md`.
