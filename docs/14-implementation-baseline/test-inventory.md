# Current Test Inventory

Status: Verified baseline  
Authority: `tests/` collection and executed commands  
Owner: Test owner  
Verified: 2026-07-14

## Backend suite

The current canonical-LF local-profile collection contains 385 tests: 354 pass and 31 integration-profile tests skip when external services are not configured. Historical task-by-task breakdowns below record the verified growth of this suite. The canonical commands are:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
backend\.venv\Scripts\python.exe -m pytest -q
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

The AGT-003 trace-persistence gate passed **6 tests**, its assistant/evidence/retrieval/service regression passed **108 tests**, and the local-profile full suite passed **228 tests with 29 integration-profile tests skipped**. The matrix verifies atomic local writes/rollback, repository-scoped replay, ordered allowlisted events, credential redaction, source/prompt exclusion from trace payloads, non-allowlisted payload rejection, fail-closed ChatService persistence and accepted production-table mapping. PostgreSQL runtime integration remains covered by the declared integration profile and was skipped in this local run; public history, automated retention execution and accepted agent thresholds remain outside this evidence.

The AGT-004 provider-evidence gate passed **7 tests**, its assistant/evidence/retrieval/service regression passed **121 tests**, and the canonical-LF local-profile full suite passed **342 tests with 31 integration-profile tests skipped**. The matrix verifies exact selected source content, active owner/index binding, source hash/range/blocked checks, all-or-nothing context budgeting, current-source re-read for selected saved evidence, untrusted-source prompt delimiting, provider-outage fallback, citation allowlisting and source exclusion from persisted traces. The default fake provider remains deliberately unconfigured; real-provider answer quality, latency, cost and accepted thresholds remain unverified.

The AGT-005 context gate passed **5 focused tests** and the assistant/retrieval/API-contract gate passed **81 tests**. A canonical-LF full local-profile run passed **347 tests with 31 integration-profile tests skipped**. The main Windows checkout passed 329 tests and exposed the same 18 evaluation-fixture failures caused by CRLF hash drift in `backend/auth_service.py`; no AGT-005 test failed. Frontend typecheck, lint, all **113 tests across 16 files**, and production build pass. The matrix covers request bounds/raw-source exclusion, owner/hash/range/symbol rejection before retrieval, context-biased retrieval with unchanged classification, stable 422 mapping, Code/Overview context display and removal, exact request serialization and context-free compatibility.

The EVA-001 clean-environment gate passed **19 targeted tests**, its evaluation/retrieval/evidence/assistant compatibility regression passed **95 tests**, and the local-profile full suite passed **247 tests with 29 integration-profile tests skipped**. The matrix validates content-addressed dataset/fixture identities, bounded dataset/candidate/file inputs, exact/lexical/semantic/graph/negative/ambiguous cases, source hash/range/path safety, three same-input baselines, hand-computed metric formulas, input-order invariance, frozen run identities, reviewed aggregate regressions, checksums and CLI export. Deterministic semantic observations do not establish real provider quality, production latency/load, answer quality or accepted release thresholds.

The EVA-002 clean-environment gate passed **13 targeted policy tests**, its combined evaluation/graph/readiness/incremental/equivalence/assistant suite passed **93 tests**, and the local-profile full suite passed **260 tests with 29 integration-profile tests skipped**. The matrix verifies content-addressed smoke configuration, identity/integrity binding, controlled finite unique rules, order invariance, completed-case enforcement, missing/errored/non-finite/below-floor failures, deterministic decision checksum and CLI exit behavior. The named GitHub Actions smoke job passed for commit `2aba763` in both push and pull-request triggers; this does not establish production thresholds.

| Module | Tests | Main coverage |
| --- | ---: | --- |
| `test_codebase_service.py` | 23 | import preview/confirm/cancel, ZIP security, indexing, incremental behavior, stale/selected evidence, deletion |
| `security/test_import_acquisition_security.py` | 26 | archive traversal/link/special/collision/depth/count/size/ratio/stream limits; folder duplicate/count/byte cleanup; canonical hardened offline Git acquisition |
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
| `assistant/test_trace_persistence.py` | 6 | atomic local persistence/rollback, redaction, allowlist rejection, ordered owned replay, ChatService fail-closed behavior and accepted production trace schema mapping |
| `assistant/test_provider_evidence_context.py` | 7 | selected/current whole source context, hash/range/blocked/budget rejection, saved-evidence source reads, prompt-injection delimiting, provider fallback, citation restriction and trace privacy |
| `assistant/test_request_context.py` | 5 | bounded page/file/line/symbol shape, raw-source exclusion, owner/hash/range/symbol validation, retrieval anchoring, stable API rejection and pre-retrieval failure |
| `evaluation/` | 32 | versioned bounded dataset/fixture validation, hand-computed retrieval metrics, three baseline methods, reproducible checksums, content-addressed CI smoke policy, identity/integrity rules, deterministic diagnostics and CLI pass/fail export |
| `test_file_rules.py` | 5 | secret filtering, supported files, language detection/registry |
| `test_service_boundaries.py` | 9 | API dependency boundaries, shared composition root, scanner/parser/graph/retrieval/LLM boundary behavior |
| `test_graph_projection.py` | 7 | server maxima, truncation/count consistency, filter/support/direction/depth traversal, missing roots, deterministic 1,000-node ordering, active-version conflict mapping |
| `test_api_contract.py` | 6 | OpenAPI drift, route/auth inventory, operation IDs, schema compatibility exports, route ownership and bounded graph parameters/disclosure fields |
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
- ZIP traversal, links, special files, normalized collisions and quota abuse are rejected before unsafe writes; actual extraction bytes are bounded and nested archives are skipped.
- Folder and mocked public-Git acquisition enforce normalized path/tree quotas and remove failed staging without network access.
- Managed repository deletion removes persisted records and managed source.
- Fake LLM provider is treated as not configured.

## Missing or incomplete suites

- No end-to-end FastAPI `TestClient` behavior suite for all 43 handlers; structural route/auth coverage is present.
- PostgreSQL/Alembic migration coverage exists for DAT-002; backup/restore and live production upgrade drills remain future operational work.
- Lease/heartbeat, bounded retry, durable cancellation, stale-generation fencing, and Redis worker-loss recovery are covered by JOB-004. Immutable filesystem artifacts and terminal manifest publication are covered by IDX-001. Typed phase contracts and storage-backed validated-prefix checkpoint resume are covered by IDX-002. Deterministic readiness validation and fenced atomic activation are covered by IDX-003. IDX-004 adds the bounded planner and exact comparison harness; production worker composition remains later authorized work.
- The synthetic full/incremental comparison fixture matrix is verified, but no production parser/resolver/graph pipeline fixture has yet populated and passed the canonical equivalence snapshot.
- Python has one canonical file-local adapter/IR authority, typed import/call references, reference-derived graph candidates and tested compatibility projections. Cross-file symbol/inheritance/dynamic resolution, CFG/DFG/non-Python candidates, global canonical graph composition and production pipeline composition remain incomplete.
- Capability readiness calculation is typed and deterministic, but current production manifest/worker composition has not yet supplied or persisted the calculated records.
- Frontend coverage includes 114 Vitest tests across 16 files spanning routing/application, API client, import, server-state policy, bounded graph, contextual assistant requests, stateful conversation replay and workspace components. UI-004 has six deterministic Chromium tests; UI-005 adds four Settings/Evaluation Chromium tests covering success, permission, retry recovery, unavailable capability and repository/index context. Axe serious/critical checks cover both UI-005 primary surfaces. Broader MSW API contracts and accepted release performance budgets remain absent.
- SEC-001 now has adversarial archive/folder/Git acquisition coverage. Parser isolation, content secret scanning, rate/abuse load, auth, container/network, dependency scan, backup/restore, and broader release evidence remain absent.
- EVA-001 adds a versioned deterministic retrieval dataset and keyword/semantic-fixture/hybrid comparison, but no claim-level support benchmark, real embedding/provider run, accepted quality/latency threshold, answer judge or load qualification.
- AGT-001 adds bounded typed single-round routing and tool execution, but no multi-round sufficiency repair, claim/citation validator, persistent trace or agent evaluation threshold.
- AGT-003 adds atomic redacted conversation/structured-trace persistence and owned internal replay, but no semantic entailment model/benchmark, public history API, automated retention executor or accepted agent threshold.
- AGT-004 gives the optional provider exact validated selected source spans instead of citation metadata alone, but does not qualify a real provider, add frontend entity context/history, or introduce any source modification capability.
- AGT-005 adds visible removable Code source context and Overview page context, but not graph/API context, conversation replay, multi-turn memory, attachments or provider qualification.
- AGT-006 adds repository-owned bounded history/replay and deterministic multi-turn intent memory, but not Ollama/provider qualification, dense embeddings, retention execution or accepted agent thresholds.

## Collection boundary

Root `pytest.ini` sets `testpaths = tests` and excludes storage, dependency, virtualenv, and build directories. The EVA-002 clean local-profile run collected 289 project tests, passed 260 and skipped 29 existing integration-profile tests; no imported repository test participated.

The completed SEC-001 focused gate passes **49 tests** (26 adversarial acquisition tests plus 23 ingestion/service regressions), and the mandatory full backend suite passes **294 tests with 29 integration-profile tests skipped**. The previously observed evaluation failures were caused by Windows CRLF checkout conversion of the synthetic fixture; restoring its Git-index LF bytes made the declared hashes validate without changing dataset records, manifests, thresholds, or gates.

The SEC-002 focused auth/API gate passes **14 tests with one PostgreSQL-profile skip**. With PostgreSQL 18.4 enabled, the combined migration and auth integration gate passes **17 tests**, including fresh/supported migration, append-only audit, zero schema drift and raw-credential exclusion. The mandatory local-profile full backend suite passes **302 tests with 31 integration-profile skips**. The matrix covers one-time bootstrap, fixed scrypt parameters, session absolute/idle/revocation behavior, Origin/CSRF enforcement, named token one-time disclosure/expiry/revocation, non-disclosing repository denial, safe audits, recovery rotation and production fail-closed configuration.

## Frontend gates

| Command | Result |
| --- | --- |
| `npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx src/pages/workspace/UI004Workspace.test.tsx src/App.test.tsx` | Passed: 14 tests across 3 files |
| `npm.cmd test -- --run src/pages/workspace/UI005Workspace.test.tsx src/features/server-state/serverState.test.tsx src/App.test.tsx` | Passed: 22 tests across 3 files |
| `npm.cmd test -- --run` | Passed: 51 tests across 8 files |
| `npm.cmd run lint` | Passed with 0 errors |
| `npx.cmd tsc -b` | Passed |
| `npm.cmd run build` | Passed after clean `npm ci`: 131 modules; JS 378.67 kB (115.46 kB gzip), CSS 37.19 kB (8.79 kB gzip) |
| AGT-005 `npx.cmd tsc -b`; `npm.cmd run lint`; `npm.cmd test -- --run`; `npm.cmd run build` | Passed: 113 tests across 16 files; 147 modules; JS 503.45 kB (143.39 kB gzip), CSS 91.78 kB (19.16 kB gzip); existing >500 kB chunk warning remains |
| AGT-006 `npx.cmd tsc -b`; `npm.cmd run lint`; `npm.cmd test -- --run`; `npm.cmd run build` | Passed: 114 tests across 16 files; 147 modules; JS 506.64 kB (144.09 kB gzip), CSS 92.92 kB (19.39 kB gzip); existing >500 kB chunk warning remains |
| `npm.cmd run test:e2e:ui004` | Passed: 6 Chromium tests; axe serious/critical = 0; 12/80/220 returned nodes and 11/79/219 edges rendered |
| `npm.cmd run test:e2e:ui005` | Passed: 4 Chromium tests; Settings success/permission/retry recovery and Evaluation context/unavailable; axe serious/critical = 0 |

`FND-005` added a minimal Vitest/jsdom/Testing Library harness, preserved the abort error cause in `src/api/client.ts`, and moved the three automatic-preview effects after their called declarations in `src/hooks/useImportController.ts`. Targeted tests cover the timeout cause and folder/ZIP/GitHub automatic previews. Broader frontend behavior and E2E coverage remain future UI work.

`UI-001` adds deterministic canonical route parsing/building plus application tests for root redirect, direct source/line and owned-evidence restoration, URL-owned search state, missing/unsafe recovery, and browser history. A clean Vite preview returned the canonical source deep link with HTTP 200. MSW API contracts, accessibility automation and Playwright flows remain future Phase 6 gates.

`UI-002` adds deterministic tests for repository/version query keys, cancellation, bounded retry, terminal/hidden polling, async-state classification, same-key cache retention and mutation invalidation. Application/import tests verify QueryClient integration and retry recovery. The exact lock survived `npm ci` unchanged; clean typecheck, lint, targeted/full tests and production build pass.

`UI-003` adds seven service tests and one API-contract test for bounded deterministic graph projections, plus component/query tests proving normalized projection identity, full rendering of the 220-node server maximum, limited-state disclosure, bounded expansion and keyboard-native controls/relation fallback. A clean LF checkout passed 31 targeted and the full 297-test backend collection (268 passed, 29 integration-profile skips); frontend targeted/full/lint/typecheck/build gates also pass.

`UI-004` adds component coverage for complete SVG edge rendering, selected-node context, retained accessible relations, architecture entry, source-backed tour steps and direct/inferred/unknown impact language. Its deterministic Playwright fixture covers the Architecture-to-source, Graph focus/relation/reduced-motion and current Impact journeys; axe reports no serious/critical violations, and Chromium renders the full 12/80/220-node projections. Clean install, 14 targeted tests, all 45 frontend tests, lint, TypeScript and production build pass locally. The named GitHub Actions job passed for commit `5ef247d`; no Phase 6 release claim is inferred from task completion.

`UI-005` adds exact global Settings/ignore-pattern query identities, allowlisted non-secret rendering, limited/unavailable async states, honest unsupported-action language and repository/index-bound Evaluation context. Clean install, 22 focused tests, all 51 frontend tests, lint, TypeScript, build, four UI-005 browser tests and all six UI-004 regressions pass locally. The named GitHub Actions job passed for commit `2f22d77`; interactive evaluation APIs, mutable settings, provider tests and accepted performance thresholds remain outside this slice.
