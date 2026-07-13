# Test Fixture Catalog

Status: Verified baseline and growth contract  
Authority: Synthetic repository fixtures  
Owner: Test and intelligence owners  
Verified: 2026-07-12

Fixtures are small, synthetic, secret-free repositories. They must never point at production repositories or be replaced with imported runtime content from `storage/`.

## `fastapi_react_sample`

Path: `tests/fixtures/fastapi_react_sample/`

Purpose: exercise a cross-stack login flow from React/TypeScript to FastAPI/Python, service logic, token helper, model, documentation, evidence and graph relations.

| Expected fact | Source |
| --- | --- |
| Frontend component `LoginPage` | `frontend/src/pages/LoginPage.tsx` |
| Frontend function `login` | `frontend/src/services/authApi.ts` |
| API call `POST /api/auth/login` | `authApi.ts` |
| FastAPI endpoints `POST /login`, `GET /me` under `/api/auth` | `backend/app/api/auth/routes.py`, `backend/app/main.py` |
| Service `AuthService.authenticate_user` | `backend/app/services/auth_service.py` |
| Token function `create_access_token` | `backend/app/core/security.py` |
| Model `User` | `backend/app/models/user.py` |
| Documented login flow | `README.md` |

Expected relationships include frontend component → API client, API client → endpoint, endpoint → service, endpoint → token helper, application → router, and related model/document evidence. The fixture intentionally uses simple syntax and deterministic literal routes; it does not test dependency injection, dynamic dispatch, generated routes, monorepo aliases, or framework ambiguity.

## Required future fixture matrix

| Fixture | Purpose | Needed before |
| --- | --- | --- |
| `typescript_react_cases` | exports, components, hooks, path aliases, fetch clients and dynamic imports | structural TS capability claim |
| `multi_framework_endpoints` | FastAPI, Flask and explicitly unsupported/dynamic routing | endpoint accuracy report |
| `incremental_change_matrix` | edit/add/delete/move/rename/signature changes | `IDX-004` equivalence gate |
| `evidence_security_cases` | stale, missing, out-of-range, secret-like and cross-repository evidence | `RET-003` |
| `retrieval_benchmark_repo` | exact, lexical, semantic, graph, negative and ambiguous questions | `EVA-001` |
| `large_projection_synthetic` | bounded graph/coverage/performance behavior | `UI-003` |
| `unsafe_import_archives` | traversal, duplicate, symlink, nested, bomb-ratio, depth and quota cases | `SEC-001` |

## `python_parser_golden`

Path: `tests/intelligence/test_parser_golden.py` (inline synthetic source; no runtime repository input)

Purpose: verify the `parsed-file/v1` Python adapter envelope, ownership and producer identities, canonical file key, content hash, imports/aliases, nested qualified symbols, deterministic serialization, line-shift identity, malformed syntax, path rejection, single-adapter invocation, and safe compatibility fallback.

The reviewed expected values are declared directly in the test so semantic changes require an intentional diff. Resolver outcomes, non-Python capability claims, and graph normalization remain outside this fixture and belong to later `INT-*` tasks.

## `python_resolution_cases`

Path: `tests/intelligence/test_resolver_accuracy.py` (inline synthetic source and declared file catalogs)

Purpose: exercise absolute/relative imports, aliases, local functions, `self.method`, qualified class methods, duplicate-name ambiguity, builtin/stdlib/framework/external classification, missing targets, dynamic attributes, deterministic catalog ordering and ambiguous internal module candidates.

Every discovered import/call has one reviewed `resolved`, `ambiguous`, or `unresolved` outcome. The fixture does not claim cross-file symbol resolution, inheritance/MRO, dynamic dispatch, non-Python rules, framework route-handler resolution or canonical graph validation.

## `graph_invalid_candidates`

Path: `tests/intelligence/test_graph_candidates.py` (inline synthetic candidates and a valid Python pipeline fixture)

Purpose: verify provenance-bearing reference-derived nodes/edges, zero-critical valid output, canonical inverse-direction conversion, exact duplicate audit, deterministic input ordering, and critical rejection of dangling endpoints, conflicting canonical keys, invalid shape/relation/key, missing provenance, ownership mismatch and below-policy inferred confidence.

The confidence minimum is an explicit synthetic policy input and is not a universal production threshold. This fixture does not cover CFG/DFG candidate conversion, non-Python producers, graph query/projection behavior, persisted candidates or capability readiness.

## Fixture acceptance

Every fixture declares expected files/entities/relations/evidence, allowed alternatives, intentionally unresolved cases, and owning tests. Golden outputs change only through a reviewed semantic task; do not refresh them merely to pass a regression.
