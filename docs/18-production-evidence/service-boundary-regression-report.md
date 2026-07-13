# Service Boundary Regression Report

Status: Verified

Owner: Project maintainer

Verified: 2026-07-13

## Scope

This report records `FND-004` evidence for replacing API dependencies on the broad `CodebaseService` facade with domain-specific application boundaries. It does not claim durable persistence, jobs, authentication, or other downstream production semantics.

## Implemented boundary

- One `ApplicationContainer` constructs the existing shared store and focused services.
- Eight typed FastAPI dependency providers expose repository, import, indexing, exploration, assistant, graph, search, and settings boundaries.
- All 42 versioned handlers use their owning boundary and none imports the compatibility facade.
- `CodebaseService` remains available for existing direct callers and reuses the same composition implementation.

## Verification results

| Gate | Result |
| --- | --- |
| `backend/.venv/Scripts/python.exe backend/scripts/export_openapi.py --check` | Pass: committed artifact is up to date; no wire-contract change |
| `backend/.venv/Scripts/python.exe -m pytest tests/test_service_boundaries.py tests/test_api_contract.py tests/test_codebase_service.py -q` | Pass: 37 tests in 10.54 s; 1 existing duplicate-ZIP warning |
| `backend/.venv/Scripts/python.exe -m pytest tests -q` | Pass: 60 tests in 14.71 s; 1 existing duplicate-ZIP warning |

The structural tests verify the expected provider on every route, reject compatibility-facade imports in route modules, and prove that all providers return stable instances backed by the same repository service. No schema, database, model, frontend, fixture, dependency, or runtime-storage file was changed.
