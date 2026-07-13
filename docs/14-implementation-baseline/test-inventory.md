# Current Test Inventory

Status: Verified baseline  
Authority: `tests/` collection and executed commands  
Owner: Test owner  
Verified: 2026-07-13

## Backend suite

The repository contains 251 pytest tests: 60 existing behavior tests, 33 PostgreSQL migration, repository, job-state/resilience, and Redis queue tests, 19 immutable artifact/configuration tests, 9 typed phase/checkpoint tests, 11 validation/atomic-activation tests, 18 incremental-planning/equivalence tests, 11 canonical parser golden tests, 5 canonical resolver accuracy tests, 4 graph-candidate normalization tests, 11 capability-readiness invariant tests, 16 typed retrieval/classification tests, 18 ranking regression tests, 14 evidence/context tests, 12 bounded workflow/tool tests, and 10 sufficiency/citation tests. The canonical verified commands are:

```powershell
backend\.venv-clean\Scripts\python.exe -m pytest tests -q
backend\.venv-clean\Scripts\python.exe -m pytest -q
```

With `TEST_POSTGRES_ADMIN_URL` and `TEST_REDIS_URL` pointing to the pinned integration services, the latest locked-environment run passed **132 tests with 1 existing duplicate-ZIP warning and 1 dependency deprecation warning**. PostgreSQL/Redis coverage includes migration, repository, job/version transition, active-job conflict, artifact metadata immutability, ownership, rollback, queue payload, broker outage, concurrent claim, lease heartbeat/fencing, bounded retry, durable cancellation, stale-attempt replacement, worker-loss recovery, validation persistence, and atomic activation/failed-build-preservation gates. Filesystem coverage adds safe logical keys, immutable atomic finalization, exact checksum/size verification, deterministic manifests, corruption rejection, and concurrent idempotent writes.

The IDX-003 targeted local-profile indexing run passed **15 tests with 5 PostgreSQL activation tests skipped**. With the pinned integration profile enabled, its combined job-state/indexing gate passed all 24 tests and the full backend suite passed all 132 tests.

The IDX-004 synthetic-metadata gates passed **18 targeted tests**, **33 indexing tests with 5 PostgreSQL tests skipped**, and the local-profile full suite passed **121 tests with 29 integration-profile tests skipped**. These tests verify deterministic planning and comparison mechanics; they do not claim equivalence of production parser/resolver/graph outputs.

The INT-001 golden gate passed **11 tests**, its parser/code-analysis regression passed **27 tests**, and the local-profile full suite passed **132 tests with 29 integration-profile tests skipped**. The golden gate verifies one canonical Python adapter/IR boundary and its current-state compatibility projection; it does not claim resolver, non-Python IR, canonical graph, or production pipeline equivalence.

The INT-002 resolution gate passed **5 tests**, its combined intelligence/code-analysis regression passed **34 tests**, and the local-profile full suite passed **137 tests with 29 integration-profile tests skipped**. It verifies deterministic typed Python import/call outcomes and compatibility graph projection; it does not claim cross-file symbol, inheritance/dynamic, non-Python, canonical graph or production pipeline coverage.

The INT-003 graph-candidate gate passed **4 tests**, its combined intelligence/code-analysis regression passed **38 tests**, and the local-profile full suite passed **141 tests with 29 integration-profile tests skipped**. It verifies reference-derived candidate provenance, normalization/audit, invalid-candidate rejection and zero-critical compatibility gating; CFG/DFG/non-Python/global graph composition remains outside this evidence.

The INT-004 readiness gate passed **11 tests**, its combined intelligence/activation regression passed **37 tests with 5 PostgreSQL tests skipped**, and the local-profile full suite passed **152 tests with 29 integration-profile tests skipped**. It verifies deterministic readiness calculation and manifest-compatible output; production manifest/worker composition remains outside this evidence.

The RET-001 typed retrieval gate passed **16 tests**, its retrieval/service/code-analysis compatibility regression passed **43 tests**, and the local-profile full suite passed **168 tests with 29 integration-profile tests skipped**. The matrix covers all controlled retriever types, deterministic classification/identity/rank/projection, ownership rejection, empty queries and unrelated insufficient-evidence queries. Versioned fusion, benchmark thresholds and evidence selection remain outside this evidence.

The RET-002 ranking gate passed **18 tests**, its retrieval/service/code-analysis regression passed **61 tests**, and the local-profile full suite passed **186 tests with 29 integration-profile tests skipped**. The matrix verifies canonical configuration identity, hand-computed weighted RRF, bounded score projection, ownership/support/retriever/limit filters, source-span deduplication, deterministic contribution merging/ties, input-order/raw-scale invariance and insufficient-evidence preservation. Learned ranking and accepted quality/latency thresholds remain outside this evidence.

The RET-003 evidence/context gate passed **14 tests**, its evidence/retrieval/service regression passed **80 tests**, and the local-profile full suite passed **200 tests with 29 integration-profile tests skipped**. The matrix verifies owner/freshness/source/hash/range/blocked/support validation, deterministic content-bound evidence identity, idempotent selected persistence, source diversity, input-order invariance, whole-block budget accounting, explicit omissions and insufficient multi-step coverage. Claim-level support validation and accepted quality/latency thresholds remain outside this evidence.

The AGT-001 bounded workflow/tool gate passed **12 tests**, its assistant/evidence/retrieval/service regression passed **92 tests**, and the local-profile full suite passed **212 tests with 29 integration-profile tests skipped**. The matrix verifies canonical workflow configuration, typed serializable interchange, registry identity/allowlist/version/ownership, exact avoidance, one-time hybrid fallback, multi-step routing, tool-call/time/cancellation boundaries, equivalent-call deduplication, safe tool failures and prompt-like input isolation. Multi-round sufficiency repair, claim/citation validation and persistent traces remain outside this evidence.

The AGT-002 sufficiency/citation gate passed **10 tests**, its assistant/evidence/retrieval/service regression passed **102 tests**, and the local-profile full suite passed **222 tests with 29 integration-profile tests skipped**. The matrix verifies question-specific strong-support/coverage requirements, controlled repair decisions, heuristic-only refusal, selected/current citation binding, duplicate/unbound/scope/stale/cross-owner rejection, provider response parsing and provider avoidance for insufficient evidence. Semantic entailment benchmarks and persistent traces remain outside this evidence.

| Module | Tests | Main coverage |
| --- | ---: | --- |
| `test_codebase_service.py` | 23 | import preview/confirm/cancel, ZIP security, indexing, incremental behavior, stale/selected evidence, deletion |
| `test_code_analysis.py` | 18 | stable symbol IDs, CFG/DFG/CPG-related graph behavior, resolver, projections, hybrid retrieval, impact, enrichment, diagnostics |
| `intelligence/test_parser_golden.py` | 11 | parsed-file envelope/provenance, aliases/nested symbols, deterministic serialization, line-shift identity, malformed syntax, path safety, single adapter authority and compatibility fallback |
| `intelligence/test_resolver_accuracy.py` | 5 | typed reference ownership/outcomes, relative/internal imports, aliases, local/class calls, ambiguity, unresolved reasons and deterministic ordering |
| `intelligence/test_graph_candidates.py` | 4 | candidate provenance, zero-critical valid pipeline, inverse/duplicate audit, critical invalid matrix and deterministic normalization |
| `intelligence/test_capability_readiness.py` | 11 | all readiness states, artifact/profile/validation/freshness/provider/dependency rules, activation summary, determinism and fail-closed input contracts |
| `retrieval/test_typed_retrieval.py` | 16 | typed classification/request/candidates, all retriever adapters, stable identities/ranks/hybrid projection, ownership rejection and insufficient-evidence negatives |
| `retrieval/test_ranking.py` | 18 | canonical ranking config identity/validation, hand-computed RRF, filters/limits, dedup/merge, support/tie order, raw-scale/input-order invariance and bounded projection |
| `evidence/test_evidence_context.py` | 14 | ownership/freshness/source/hash/range/blocked/support validation, stable evidence IDs, idempotent persistence, diversity, whole-block budgets, omissions, insufficient coverage and workflow projection |
| `assistant/test_bounded_workflow_tools.py` | 12 | canonical workflow configuration, typed tool interchange, immutable allowlist identity, ownership/version rejection, exact/hybrid routing, budgets, cancellation, deduplication, safe failures and prompt-like input isolation |
| `assistant/test_sufficiency_citation_repair.py` | 10 | question-specific sufficiency, controlled repair decisions, heuristic refusal, current/selected claim-citation binding, duplicate/scope/stale/cross-owner rejection and provider fail-closed behavior |
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
- Python has one canonical file-local adapter/IR authority, typed import/call references, reference-derived graph candidates and tested compatibility projections. Cross-file symbol/inheritance/dynamic resolution, CFG/DFG/non-Python candidates, global canonical graph composition and production pipeline composition remain incomplete.
- Capability readiness calculation is typed and deterministic, but current production manifest/worker composition has not yet supplied or persisted the calculated records.
- Frontend coverage is limited to four targeted timeout/import-preview tests; no broad component, MSW contract, accessibility, or Playwright suite exists.
- No load, resilience, backup/restore, deployment, container, dependency, or security scan evidence.
- RET-003 adds deterministic validated evidence selection and whole-span context budgeting, but no claim-level support validator, versioned evaluation dataset or accepted quality/latency benchmark comparing keyword, naive vector, and production hybrid workflows.
- AGT-001 adds bounded typed single-round routing and tool execution, but no multi-round sufficiency repair, claim/citation validator, persistent trace or agent evaluation threshold.
- AGT-002 adds one bounded deterministic repair and structural claim/citation validation, but no semantic entailment model/benchmark, persistent trace or accepted agent threshold.

## Collection boundary

Root `pytest.ini` sets `testpaths = tests` and excludes storage, dependency, virtualenv, and build directories. The AGT-002 local-profile run collected 251 project tests, passed 222 and skipped 29 integration-profile tests; no imported repository test participated.

## Frontend gates

| Command | Result |
| --- | --- |
| `npm.cmd run test` | Passed: 4 tests across 2 files |
| `npm.cmd run lint` | Passed with 0 errors |
| `npm.cmd run build` | Passed |

`FND-005` added a minimal Vitest/jsdom/Testing Library harness, preserved the abort error cause in `src/api/client.ts`, and moved the three automatic-preview effects after their called declarations in `src/hooks/useImportController.ts`. Targeted tests cover the timeout cause and folder/ZIP/GitHub automatic previews. Broader frontend behavior and E2E coverage remain future UI work.
