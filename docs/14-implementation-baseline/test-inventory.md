# Current Test Inventory

Status: Verified baseline  
Authority: `tests/` collection and executed commands  
Owner: Test owner  
Verified: 2026-07-13

## Backend suite

The repository contains 161 pytest tests: 60 existing behavior tests, 33 PostgreSQL migration, repository, job-state/resilience, and Redis queue tests, 19 immutable artifact/configuration tests, 9 typed phase/checkpoint tests, 11 validation/atomic-activation tests, 18 incremental-planning/equivalence tests, and 11 canonical parser golden tests. The canonical verified commands are:

```powershell
backend\.venv-clean\Scripts\python.exe -m pytest tests -q
backend\.venv-clean\Scripts\python.exe -m pytest -q
```

With `TEST_POSTGRES_ADMIN_URL` and `TEST_REDIS_URL` pointing to the pinned integration services, the latest locked-environment run passed **132 tests with 1 existing duplicate-ZIP warning and 1 dependency deprecation warning**. PostgreSQL/Redis coverage includes migration, repository, job/version transition, active-job conflict, artifact metadata immutability, ownership, rollback, queue payload, broker outage, concurrent claim, lease heartbeat/fencing, bounded retry, durable cancellation, stale-attempt replacement, worker-loss recovery, validation persistence, and atomic activation/failed-build-preservation gates. Filesystem coverage adds safe logical keys, immutable atomic finalization, exact checksum/size verification, deterministic manifests, corruption rejection, and concurrent idempotent writes.

The IDX-003 targeted local-profile indexing run passed **15 tests with 5 PostgreSQL activation tests skipped**. With the pinned integration profile enabled, its combined job-state/indexing gate passed all 24 tests and the full backend suite passed all 132 tests.

The IDX-004 synthetic-metadata gates passed **18 targeted tests**, **33 indexing tests with 5 PostgreSQL tests skipped**, and the local-profile full suite passed **121 tests with 29 integration-profile tests skipped**. These tests verify deterministic planning and comparison mechanics; they do not claim equivalence of production parser/resolver/graph outputs.

The INT-001 golden gate passed **11 tests**, its parser/code-analysis regression passed **27 tests**, and the local-profile full suite passed **132 tests with 29 integration-profile tests skipped**. The golden gate verifies one canonical Python adapter/IR boundary and its current-state compatibility projection; it does not claim resolver, non-Python IR, canonical graph, or production pipeline equivalence.

| Module | Tests | Main coverage |
| --- | ---: | --- |
| `test_codebase_service.py` | 23 | import preview/confirm/cancel, ZIP security, indexing, incremental behavior, stale/selected evidence, deletion |
| `test_code_analysis.py` | 18 | stable symbol IDs, CFG/DFG/CPG-related graph behavior, resolver, projections, hybrid retrieval, impact, enrichment, diagnostics |
| `intelligence/test_parser_golden.py` | 11 | parsed-file envelope/provenance, aliases/nested symbols, deterministic serialization, line-shift identity, malformed syntax, path safety, single adapter authority and compatibility fallback |
| `test_file_rules.py` | 5 | secret filtering, supported files, language detection/registry |
| `test_service_boundaries.py` | 9 | API dependency boundaries, shared composition root, scanner/parser/graph/retrieval/LLM boundary behavior |
| `test_api_contract.py` | 5 | OpenAPI drift, route/auth inventory, operation IDs, schema compatibility exports, route ownership |
| `artifacts/test_artifact_store.py` and `test_manifest.py` | 18 | Safe keys, filesystem staging/finalization, immutable retries/conflicts, verified reads, canonical manifest validation and publication |
| `indexing/test_phase_contracts.py`, `test_phase_pipeline.py`, `test_validation_activation.py`, `test_incremental_planner.py`, and `test_equivalence_service.py` | 38 | Typed phases/checkpoints, deterministic validation/activation, bounded typed affected-set planning, safe full fallback, and exact canonical-family equivalence diagnostics |
| `migrations/test_migrations.py` | 7 | PostgreSQL 18.4 empty install, drift, constraints, rollback/recovery, and supported SQLite mapping |
| `persistence/test_production_repository.py` | 13 | Production PostgreSQL/Redis/lease/artifact-root profile validation, adapter selection, lease-preserving compatibility progress, job building-to-active lifecycle, PostgreSQL repository/evidence CRUD, path and ownership rollback |
| `jobs/test_job_state_store.py` | 4 | Transactional submission, declared/stale transitions, one-active-job conflict, immutable artifact ownership |
| `jobs/test_job_queue.py` | 5 | One-ID payload, concurrent duplicate gate, broker-outage preservation, stable publication error, Redis worker restart delivery |
| `jobs/test_job_resilience.py` | 5 | Atomic claim, heartbeat extension, stale-generation fencing, durable cancellation, bounded retry, and Redis redelivery after worker loss |

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
- PostgreSQL/Alembic migration coverage exists for DAT-002; backup/restore and live production upgrade drills remain future operational work.
- Lease/heartbeat, bounded retry, durable cancellation, stale-generation fencing, and Redis worker-loss recovery are covered by JOB-004. Immutable filesystem artifacts and terminal manifest publication are covered by IDX-001. Typed phase contracts and storage-backed validated-prefix checkpoint resume are covered by IDX-002. Deterministic readiness validation and fenced atomic activation are covered by IDX-003. IDX-004 adds the bounded planner and exact comparison harness; production worker composition remains later authorized work.
- The synthetic full/incremental comparison fixture matrix is verified, but no production parser/resolver/graph pipeline fixture has yet populated and passed the canonical equivalence snapshot.
- Python has one canonical file-local adapter/IR authority and a tested compatibility projection. Non-Python adapters, typed resolver output, canonical graph candidates, and production pipeline composition remain incomplete.
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
