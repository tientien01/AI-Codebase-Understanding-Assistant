# Current Test Inventory

Status: Verified baseline  
Authority: `tests/` collection and executed commands  
Owner: Test owner  
Verified: 2026-07-12

## Backend suite

The repository contains 52 pytest tests across four modules. The canonical verified command is:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
```

Result on the verification date: **52 passed, 1 warning, 38.25 seconds**.

| Module | Tests | Main coverage |
| --- | ---: | --- |
| `test_codebase_service.py` | 23 | import preview/confirm/cancel, ZIP security, indexing, incremental behavior, stale/selected evidence, deletion |
| `test_code_analysis.py` | 18 | stable symbol IDs, CFG/DFG/CPG-related graph behavior, resolver, projections, hybrid retrieval, impact, enrichment, diagnostics |
| `test_file_rules.py` | 5 | secret filtering, supported files, language detection/registry |
| `test_service_boundaries.py` | 6 | scanner/parser/graph/retrieval/LLM boundary smoke behavior |

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

- No FastAPI `TestClient`/HTTP contract suite for all 43 handlers.
- No OpenAPI snapshot/drift test.
- No PostgreSQL/Alembic migration or schema-drift suite.
- No durable queue redelivery, worker crash, lease/heartbeat, broker outage, or recovery suite.
- No formal full/incremental canonical artifact equivalence report across a fixture matrix.
- No frontend component, hook, MSW contract, accessibility, or Playwright tests.
- No load, resilience, backup/restore, deployment, container, dependency, or security scan evidence.
- No versioned retrieval/answer benchmark comparing keyword, naive vector, and production hybrid workflows.

## Collection defect

Running `python -m pytest -q` from the repository root collects Python tests inside `storage/repositories/` and `storage/uploads/`. Imported repositories are untrusted and must never participate in the project's test collection. The immediate safe command explicitly names `tests/`; the production fix is a checked pytest configuration with `testpaths = tests` and exclusions for storage/dependency/build directories.

## Frontend gates

| Command | Result |
| --- | --- |
| `npm.cmd run lint` | Failed with 4 errors |
| `npm.cmd run build` | Passed |

The lint errors are one missing preserved `cause` in `src/api/client.ts` and three declaration-order/React hook immutability errors in `src/hooks/useImportController.ts`. They are baseline defects; `DOC-002` does not authorize fixes.
