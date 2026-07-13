---
id: FND-004
title: Replace broad application facade at API boundaries
status: completed
priority: P0
phase: 1
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [FND-003]
requirements: []
contracts:
  - docs/02-system-architecture/component-catalog.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/12-engineering/README.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/stack-profiles.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/api-coverage.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/api/dependencies.py
  - backend/app/api/v1/routes/**
  - backend/app/services/application/**
  - backend/app/services/codebase_service.py
  - tests/test_service_boundaries.py
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/api-coverage.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/foundation/FND-004-replace-broad-application-facade.md
  - docs/18-production-evidence/service-boundary-regression-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/db/**
  - backend/app/models/**
  - backend/app/schemas/**
  - backend/app/main.py
  - backend/scripts/export_openapi.py
  - frontend/**
  - tests/fixtures/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Every versioned route depends on a domain-specific application service instead of the system-wide CodebaseService facade.
  - One composition root supplies shared in-process collaborators without changing current persistence or job semantics.
  - The 43-operation OpenAPI artifact remains byte-stable and all existing backend behavior tests pass.
evidence_outputs:
  - docs/18-production-evidence/service-boundary-regression-report.md
---

# Task FND-004 — Replace Broad Application Facade at API Boundaries

## Context

`FND-003` separated route and schema ownership while intentionally preserving calls through the system-wide `CodebaseService` singleton. Focused ingestion, repository, indexing, exploration, retrieval, assistant, graph, impact, file, and settings services already exist, but API modules cannot depend on them independently and cannot override a narrow use-case boundary in tests.

## Objective

Remove every API route dependency on `CodebaseService`, introduce one explicit composition root with domain-specific application services and FastAPI dependency providers, and preserve the verified HTTP and backend behavior contracts.

## In scope

- Add a composition root that constructs the existing focused services once and preserves their shared in-process repository state.
- Add small application services only where one API use case must coordinate multiple existing domain services.
- Add typed FastAPI dependency providers for the service boundary used by each route.
- Change all eight versioned route modules to depend on their narrow service boundary.
- Retain `CodebaseService` as a backward-compatible adapter for existing direct callers and behavior tests, backed by the same composition implementation rather than duplicated construction rules.
- Add structural and behavior-regression tests for the new boundaries.

## Out of scope

- API/schema/OpenAPI changes, new endpoints, or generated client changes.
- Persistence, repository-store, indexing/job semantics, parser, retrieval, graph, evidence, or assistant algorithm changes.
- Durable jobs, PostgreSQL, transactions, authentication, observability, or frontend work.
- Dependency additions or upgrades.

## Existing code to reuse

- Focused services under `backend/app/services/` and their current constructor dependencies.
- `CodebaseService` forwarding behavior as the compatibility baseline.
- The eight route modules produced by `FND-003`.
- `tests/test_codebase_service.py` and the committed OpenAPI artifact as behavior and wire-contract baselines.

## Implementation sequence

1. Add boundary tests that reject direct route imports of `app.services.codebase_service` and verify domain-specific dependency providers.
2. Extract the existing service construction graph into one application composition root.
3. Add narrow orchestration services for repository deletion/upload, indexing control, assistant/evidence, and graph/impact use cases where direct focused-service delegation is insufficient.
4. Make `CodebaseService` delegate through the composition root while preserving its public methods and compatibility properties.
5. Inject narrow services into all route handlers without changing decorators, paths, request/response models, function names, or auth dependencies.
6. Run OpenAPI, targeted boundary, compatibility, and full backend gates; then record baseline and evidence.

## Data/API compatibility and migration

No data migration and no intentional API change. All routes must share one composition root so an import performed through one boundary is immediately visible to exploration, indexing, retrieval, graph, and assistant boundaries. The committed OpenAPI artifact remains the machine-readable wire regression boundary.

## Failure, security, performance, and observability requirements

- Preserve `require_api_auth` on all 42 versioned operations and existing `DomainError` behavior.
- Do not create service instances per request or split the current in-memory repository state.
- Do not read runtime storage, imported repositories, configuration secrets, or credentials during boundary verification.
- Dependency providers must be overrideable through standard FastAPI dependency overrides for future isolated route tests.
- The change must add no network, provider, database, or background-worker side effects.

## Required tests and commands

Run from the repository root with the locked Python 3.11 environment:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/export_openapi.py --check
backend/.venv/Scripts/python.exe -m pytest tests/test_service_boundaries.py tests/test_api_contract.py tests/test_codebase_service.py -q
backend/.venv/Scripts/python.exe -m pytest tests -q
git diff --check -- backend/app/api/dependencies.py backend/app/api/v1/routes backend/app/services/application backend/app/services/codebase_service.py tests/test_service_boundaries.py docs/14-implementation-baseline/source-map.md docs/14-implementation-baseline/api-coverage.md docs/14-implementation-baseline/test-inventory.md docs/16-agent-tasks/foundation/FND-004-replace-broad-application-facade.md docs/18-production-evidence/service-boundary-regression-report.md docs/project-status.md
```

## Acceptance criteria

- No versioned route module imports or references `CodebaseService` or `codebase_service`.
- Every route handler declares a typed dependency on the narrow application or focused service that owns its use case.
- One composition root owns the shared `RepositoryStore` and collaborator graph; dependency providers return stable instances from that root.
- A repository created or indexed through one boundary remains observable through all other boundaries exactly as before.
- `CodebaseService` retains its existing public methods and the complete compatibility behavior suite passes.
- The OpenAPI exporter reports no change, the targeted boundary/API/facade suite passes, and the complete backend suite passes.
- No dependency, schema, database, model, frontend, fixture, or runtime-storage file changes.

## Rollback

Restore direct route calls to the `codebase_service` singleton, restore its local constructor graph, and remove the composition root, dependency providers, application-boundary tests, and evidence file. No data rollback is required.

## Documentation and evidence updates

Update the source map, API coverage, test inventory, this task, project status, and `docs/18-production-evidence/service-boundary-regression-report.md` with exact commands and results.

## Completion evidence

- All eight versioned route modules use typed domain-specific FastAPI dependencies; no route imports or references `CodebaseService` or `codebase_service`.
- One `ApplicationContainer` constructs the shared repository store and focused collaborators. Eight stable dependency providers expose repository, import, indexing, exploration, assistant, graph, search, and settings boundaries.
- `CodebaseService` now inherits the same composition implementation and retains its existing public compatibility API.
- The committed OpenAPI artifact remained unchanged; the targeted boundary/API/facade suite passed 37 tests and the complete backend suite passed 60 tests with one existing duplicate-ZIP warning on 2026-07-13.
