---
id: FND-003
title: Split API route and schema domains without behavior change
status: completed
priority: P0
phase: 1
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [FND-001, FND-002]
requirements: []
contracts:
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/12-engineering/README.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/stack-profiles.md
allowed_paths:
  - backend/app/main.py
  - backend/app/api/v1/routes/**
  - backend/app/schemas/**
  - backend/scripts/export_openapi.py
  - tests/test_api_contract.py
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/14-implementation-baseline/api-coverage.md
  - docs/16-agent-tasks/foundation/FND-003-split-api-route-schema-domains.md
  - docs/18-production-evidence/api-contract-regression-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/services/**
  - backend/app/db/**
  - backend/app/models/**
  - frontend/**
  - tests/fixtures/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - The 43-handler HTTP surface and generated OpenAPI document remain byte-stable across the module split.
  - Route and schema ownership is separated by domain while compatibility imports remain valid.
  - Existing backend behavior passes the targeted API contract suite and complete backend suite.
evidence_outputs:
  - docs/18-production-evidence/api-contract-regression-report.md
---

# Task FND-003 — Split API Route and Schema Domains Without Behavior Change

## Context

All 42 `/api/v1` handlers are concentrated in `routes/repositories.py`, while 63 Pydantic boundary models are concentrated in `schemas/api.py`. The accepted REST contract requires a checked OpenAPI artifact and drift gate before later endpoint implementation tasks. This task changes ownership and packaging only; the verified MVP wire contract remains the regression baseline.

## Objective

Split current routes and schemas into domain modules, preserve every registered method/path/request/response contract, and commit a deterministic OpenAPI artifact with an executable drift check.

## In scope

- Capture the current FastAPI OpenAPI document before moving handlers.
- Split import-session, repository, indexing, exploration, assistant/evidence, graph/impact, search/files, and settings routes into domain modules.
- Split Pydantic models into matching domain modules with a small common module where types are shared.
- Keep `app.schemas.api` as an explicit compatibility export surface for unchanged service/test imports.
- Add a deterministic OpenAPI exporter/checker and API contract regression tests.
- Update the verified API coverage and task evidence.

## Out of scope

- Adding, removing, renaming, or implementing target production endpoints.
- Changing request/response fields, status codes, authentication, service calls, persistence, or background-job behavior.
- Moving application logic out of `codebase_service`; that belongs to `FND-004`.
- Adding dependencies, generated frontend clients, database migrations, or deployment changes.

## Existing code to reuse

- `backend/app/main.py` router registration and current route order.
- `backend/app/api/v1/routes/repositories.py` handler implementations.
- `backend/app/schemas/api.py` Pydantic definitions and public import names.
- `docs/14-implementation-baseline/api-coverage.md` as the verified 43-handler inventory.

## Implementation sequence

1. Export the pre-split OpenAPI document and add tests that check the committed artifact, route inventory, operation IDs, and compatibility imports.
2. Move schema definitions into domain modules and make `schemas/api.py` a compatibility re-export module.
3. Move handlers into domain route modules without changing decorators, signatures, response models, function names, or service calls.
4. Register routers in the original order, regenerate OpenAPI, and require a zero diff from the pre-split artifact.
5. Run targeted and full backend gates, then update evidence and status.

## Data/API compatibility and migration

No data migration and no intentional API change. The checked pre-split OpenAPI JSON is the machine-readable regression boundary for this task. Any artifact difference stops completion and requires either restoring compatibility or a separately authorized contract change.

## Failure, security, performance, and observability requirements

- Preserve the existing `require_api_auth` dependency on every versioned router.
- Do not read or expose settings secrets while generating OpenAPI.
- The exporter must be deterministic, fail non-zero on drift, and write only when explicitly requested.
- Do not initialize imported repositories or inspect `storage/` as part of contract verification.

## Required tests and commands

Run from the repository root with the locked Python 3.11 environment:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/export_openapi.py --check
backend/.venv/Scripts/python.exe -m pytest tests/test_api_contract.py -q
backend/.venv/Scripts/python.exe -m pytest tests -q
git diff --check -- backend/app/main.py backend/app/api/v1/routes backend/app/schemas backend/scripts/export_openapi.py tests/test_api_contract.py docs/06-api-and-integrations/artifacts/openapi-v1.json docs/14-implementation-baseline/api-coverage.md docs/16-agent-tasks/foundation/FND-003-split-api-route-schema-domains.md docs/18-production-evidence/api-contract-regression-report.md docs/project-status.md
```

## Acceptance criteria

- The application still registers one unversioned health handler and 42 `/api/v1` handlers with the same methods, paths, operation IDs, parameters, request bodies, response schemas, and auth dependencies.
- The deterministic OpenAPI exporter reports no difference from the artifact captured before the split.
- All 63 existing Pydantic model names remain importable from `app.schemas.api`.
- Routes and schema definitions reside in domain-owned modules; `schemas/api.py` contains compatibility exports only and `routes/repositories.py` owns only repository-management handlers.
- The targeted API contract suite and the complete backend suite pass.
- No dependency, service, database, frontend, fixture, or runtime-storage file changes.

## Rollback

Restore the monolithic route/schema modules and router imports, then remove the exporter, artifact, and regression test. No data rollback is required.

## Documentation and evidence updates

Update API coverage, this task, project status, and `docs/18-production-evidence/api-contract-regression-report.md` with exact commands and results.

## Completion evidence

- The pre-split and post-split OpenAPI artifact SHA-256 is `00FCA7CF351DC7C21AD0CE6B7690D87155DA830055DBA1C69CF79FF7EAF2F031`; `export_openapi.py --check` passed without rewriting it.
- Five targeted API contract tests passed, covering artifact equality, 43-handler inventory, auth dependencies, unique operation IDs, 63 compatibility schema exports, and domain ownership.
- The full backend suite passed 57 tests with one existing duplicate-ZIP warning on 2026-07-13.
- Eight route modules own the 42 versioned handlers and eight schema modules own all 63 existing models. No service, database, frontend, dependency, fixture, or runtime-storage file changed.
