---
id: UI-014
title: Add a dynamic Request Flow entry browser
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-012, UI-013, INT-005]
requirements: []
contracts:
  - docs/05-domain-contracts/parsing-and-graph.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
technology_docs:
  - docs/03-technology/stack-overview.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/api/v1/routes/graph.py
  - backend/app/schemas/graph.py
  - backend/app/services/graph/graph_projection_service.py
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - frontend/src/styles/pages/workspace.css
  - tests/test_graph_projection.py
  - tests/test_api_contract.py
  - docs/16-agent-tasks/production-ux/UI-014-dynamic-request-entry-browser.md
  - docs/18-production-evidence/dynamic-request-entry-browser-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/migrations/**
  - frontend/package.json
  - frontend/package-lock.json
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Request entry scopes disclose total available and currently visible entries.
  - Entry seed pages use deterministic server ordering and an explicit offset rather than a permanently hidden top-N slice.
  - Load more grows the visible entry browser without placing every repository entry on the graph canvas.
  - Current-path entities remain pinned and visible while entry browsing changes.
  - Focused backend/frontend tests, lint, typecheck, build, and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/dynamic-request-entry-browser-report.md
---

# UI-014 - Dynamic Request Entry Browser

## Context

Request Flow currently presents a bounded seed set without a complete-data affordance. The Server endpoints and Client calls controls therefore look like exhaustive tabs even when many indexed entries are hidden.

The project owner authorized this implementation in the active conversation on 2026-07-15.

## Objective

Turn entry scopes into truthful counted facets and provide deterministic progressive access to all entry points while keeping the graph focused on a selected path.

## In scope

- Deterministic offset paging for request-flow seed projections using the existing bounded projection request contract.
- Counted All, Server, and Client facets.
- Adaptive client batch size, Load more, visible/total disclosure, and current-path pinning in the same view.
- Focused regression and production evidence.

## Out of scope

- New dependencies, schema migrations, full-text indexes, arbitrary global search API, or rendering every entry on the graph canvas.
- FastAPI router-prefix reconstruction and non-JavaScript client adapters.

## Required verification

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest ..\tests\test_graph_projection.py -q
.\.venv\Scripts\python.exe -m pytest ..\tests\test_api_contract.py -q -k graph_projection
Set-Location ..\frontend
npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- backend/app/api/v1/routes/graph.py backend/app/schemas/graph.py backend/app/services/graph/graph_projection_service.py frontend/src/pages/workspace/GraphPage.tsx frontend/src/pages/workspace/GraphPage.test.tsx frontend/src/styles/pages/workspace.css tests/test_graph_projection.py tests/test_api_contract.py docs/16-agent-tasks/production-ux/UI-014-dynamic-request-entry-browser.md docs/18-production-evidence/dynamic-request-entry-browser-report.md
```

## Acceptance criteria

- Seed projections honor deterministic `neighbor_offset` paging and return the complete available total.
- Facets state `visible of total` and never imply a bounded page is exhaustive.
- Load more requests a larger bounded prefix selected from viewport-derived batch sizing.
- An endpoint reached from a client call remains visible as Current path even when it is outside the loaded entry prefix.
