# Current Test Inventory

Status: Verified baseline  
Authority: `tests/` collection and executed commands  
Owner: Test owner  
Verified: 2026-07-13

## Backend suite

The repository contains 60 pytest tests across five modules. The canonical verified commands are:

```powershell
backend\.venv-clean\Scripts\python.exe -m pytest tests -q
backend\.venv-clean\Scripts\python.exe -m pytest -q
```

The latest task-scoped run with the locked backend environment passed **60 tests with 1 warning** in 14.71 seconds. The warning is the existing duplicate-ZIP fixture warning.

| Module | Tests | Main coverage |
| --- | ---: | --- |
| `test_codebase_service.py` | 23 | import preview/confirm/cancel, ZIP security, indexing, incremental behavior, stale/selected evidence, deletion |
| `test_code_analysis.py` | 18 | stable symbol IDs, CFG/DFG/CPG-related graph behavior, resolver, projections, hybrid retrieval, impact, enrichment, diagnostics |
| `test_file_rules.py` | 5 | secret filtering, supported files, language detection/registry |
| `test_service_boundaries.py` | 9 | API dependency boundaries, shared composition root, scanner/parser/graph/retrieval/LLM boundary behavior |
| `test_api_contract.py` | 5 | OpenAPI drift, route/auth inventory, operation IDs, schema compatibility exports, route ownership |

## Strong invariants already covered

- Symbol IDs remain stable when line numbers shift.
- Graph edges reference existing nodes and schema normalization occurs.
- Failed re-index retains the previous index.
- Incremental indexing parses only changed files in the tested scenario.
- Re-index marks prior evidence stale and validation distinguishes stale/invalid evidence.
- ZIP traversal and duplicate paths are rejected; nested archives are skipped.
- Managed repository deletion removes persisted records and managed source.
- Fake LLM provider is treated as not configured.

## Missing or incomplete suites

- No end-to-end FastAPI `TestClient` behavior suite for all 43 handlers; structural route/auth coverage is present.
- No PostgreSQL/Alembic migration or schema-drift suite.
- No durable queue redelivery, worker crash, lease/heartbeat, broker outage, or recovery suite.
- No formal full/incremental canonical artifact equivalence report across a fixture matrix.
- Frontend coverage is limited to four targeted timeout/import-preview tests; no broad component, MSW contract, accessibility, or Playwright suite exists.
- No load, resilience, backup/restore, deployment, container, dependency, or security scan evidence.
- No versioned retrieval/answer benchmark comparing keyword, naive vector, and production hybrid workflows.

## Collection boundary

Root `pytest.ini` sets `testpaths = tests` and excludes storage, dependency, virtualenv, and build directories. An unscoped clean-environment run from the repository root collected and passed the same 52 project tests; no imported repository test participated.

## Frontend gates

| Command | Result |
| --- | --- |
| `npm.cmd run test` | Passed: 4 tests across 2 files |
| `npm.cmd run lint` | Passed with 0 errors |
| `npm.cmd run build` | Passed |

`FND-005` added a minimal Vitest/jsdom/Testing Library harness, preserved the abort error cause in `src/api/client.ts`, and moved the three automatic-preview effects after their called declarations in `src/hooks/useImportController.ts`. Targeted tests cover the timeout cause and folder/ZIP/GitHub automatic previews. Broader frontend behavior and E2E coverage remain future UI work.
