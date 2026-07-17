# Current Source Map

| Domain | Source |
| --- | --- |
| API | `backend/app/api/v1/routes/` |
| API dependency providers | `backend/app/api/dependencies.py` |
| Schemas | `backend/app/schemas/api.py` |
| Application composition/use cases | `backend/app/services/application/` |
| Operator auth/access/audit | `backend/app/services/security/`, `backend/app/core/auth.py`, `backend/app/api/v1/routes/auth.py`; production adapter over `operator_*`, repository ownership and `audit_events` |
| Quota-bound import acquisition | `backend/app/services/ingestion/import_policy.py`, `archive_service.py`, `upload_service.py`, `streaming_upload_service.py`, `import_session_service.py` |
| Indexing | `backend/app/services/indexing/` |
| Parsing | `backend/app/services/parsing/` |
| Deep code analysis | `backend/app/services/code_analysis/` |
| Canonical Python adapter/IR boundary | `backend/app/services/code_analysis/adapters/python_adapter.py`, `models.py`, `pipeline.py`; current-state projection in `backend/app/services/parsing/canonical_python_parser.py` |
| Canonical Python reference resolver | `backend/app/services/code_analysis/resolver.py`; typed compatibility projection in `backend/app/services/code_analysis/cpg/emitter.py` |
| Reference-derived graph candidate normalization | `backend/app/services/code_analysis/graph_candidates.py`; in-memory audit/report state in `backend/app/services/index_models.py` |
| Deterministic capability readiness calculator | `backend/app/services/code_analysis/capability_readiness.py`; output reuses `backend/app/services/indexing/validation_service.py::CapabilityReadiness` |
| Graph/projections | `backend/app/services/graph/` |
| Typed retrieval and ranking | `backend/app/services/retrieval/contracts.py`, `query_classifier.py`, `retrievers.py`, `ranking.py`; sparse/dense search adapters in `vector_search_service.py`; compatibility facade in `retrieval_service.py` |
| Validated evidence selection and context budgeting | `backend/app/services/evidence/selection.py`; persistence/citation projection in `evidence_service.py` |
| Versioned embeddings, retrieval evaluation and CI smoke gate | Shared bounded Ollama adapter plus immutable dense artifact builder/loader in `backend/app/services/embeddings/`; evaluation runner in `backend/app/services/evaluation/`; immutable dataset in `evaluation/datasets/retrieval-v1/`; RET-004 raw result in `evaluation/results/`; gate policy in `evaluation/gates/eva-002-ci.json`; synthetic fixture in `tests/fixtures/retrieval_benchmark_repo/`; named job in `.github/workflows/ci.yml` |
| Bounded assistant, request context, stateful conversation memory, sufficiency, citation validation, provider evidence, outcome disclosure and trace contracts | `backend/app/services/chat/workflow_contracts.py`, `request_context.py`, `conversation_memory.py`, `tool_registry.py`, `sufficiency.py`, `citation_validation.py`, `provider_context.py`, `trace_persistence.py`; server-declared response outcome in `chat_service.py`; compatibility provider boundary in `llm_client.py`; loopback-only native Ollama transport in `ollama_client.py` |
| Impact | `backend/app/services/impact/` |
| Persistence | `backend/app/db/`, `services/repositories/repository_store.py` |
| Production PostgreSQL metadata | `backend/app/db/production_base.py`, `backend/app/db/production_models/` |
| Alembic migrations | `backend/migrations/`, configured by `backend/alembic.ini` |
| Supported legacy upgrade | `backend/app/db/legacy_upgrade.py`, `backend/scripts/migrate_legacy_sqlite.py` |
| Production DB session/profile | `backend/app/db/production_session.py`, `backend/app/core/config.py` |
| Repository persistence port/adapters | `backend/app/services/repositories/repository_port.py`, `repository_store.py`, `production_repository_store.py` |
| Persisted job/version/artifact/lease commands | `backend/app/services/indexing/job_state_store.py` |
| Immutable artifact storage and manifest publication | `backend/app/services/artifacts/` |
| Typed indexing phases and checkpoint resume | `backend/app/services/indexing/phase_contracts.py`, `phase_pipeline.py` |
| Candidate validation and atomic activation | `backend/app/services/indexing/validation_service.py`, `activation_service.py`, `job_state_store.py` |
| Incremental affected-set planning and canonical equivalence | `backend/app/services/indexing/incremental_planner.py`, `equivalence_service.py` |
| Job queue, fenced delivery, heartbeat, retry, cancellation, and recovery | `backend/app/services/indexing/job_queue.py`, `job_delivery_service.py` |
| Dedicated indexing worker | `backend/app/workers/indexing_worker.py` |
| Frontend API/state | `frontend/src/api/`, `frontend/src/features/server-state/`, `frontend/src/hooks/`, `frontend/src/components/common/AsyncState.tsx` |
| Frontend canonical routing and recovery | `frontend/src/routing/routes.ts`, `frontend/src/App.tsx`, `frontend/src/pages/routing/` |
| Frontend surfaces | `frontend/src/pages/`, `frontend/src/components/` |
| Frontend UI-004 browser qualification | `frontend/e2e/`, `frontend/playwright.config.ts`; named job in `.github/workflows/ci.yml` |
| Frontend settings/evaluation readiness | `frontend/src/pages/workspace/SettingsPage.tsx`, `EvaluationPage.tsx`; typed reads in `frontend/src/api/server.ts` and `frontend/src/features/server-state/`; UI-005 browser gate in `frontend/e2e/ui005.spec.ts` |
| Tests/fixture | `tests/` |

The versioned API routes resolve domain-specific application boundaries from one
single-process composition root. `backend/app/services/codebase_service.py` remains
a compatibility adapter for direct callers; versioned routes no longer import it.

Agents use this map for targeted inspection and must not scan ignored dependency/build/runtime storage directories.

Import acquisition now shares one normalized relative-path identity and file/tree quota boundary across ZIP, folder, and public Git inputs. ZIP extraction validates its complete plan before writes and counts streamed bytes; folder uploads reject normalized duplicates and aggregate overflow; public Git uses a canonical GitHub URL/ref policy, isolated configuration, disabled redirects/prompts/hooks/submodules/LFS, shallow timeout-bound execution, post-clone tree validation, and failure cleanup. Container/network namespaces, parser resource isolation, content secret scanning, rate limits, auth/audit, and accepted capacity thresholds remain separate Phase 7 work.

Production operator access now uses one initialized principal, versioned scrypt password verification, opaque expiring browser sessions with strict Origin/CSRF checks, and named expiring/revocable Bearer tokens whose raw values are shown once. Repository path authorization compares the resolved principal to production ownership and emits a non-disclosing 404 plus safe audit denial. Local/test shared-token compatibility is explicit and production-forbidden. Frontend login UX, rate limiting, TLS/container exposure and automated audit retention remain later work.

`ParserService` now routes Python through one `PythonAdapter -> IRModule` authority. `CanonicalPythonParser` is the explicit projection into the current mutable `RepositoryState`; `PythonAstParser` remains only as a deprecated import-compatible class name and contains no second AST extractor. Other language parsers still use the compatibility `LanguageParser` boundary and do not yet claim production-v1 IR capability.

The Python pipeline now retains a deterministic `resolved-reference-set/v1` artifact for imports and calls before graph compatibility output. `CPGEmitter` projects typed outcomes and no longer owns target selection. Cross-file symbol/inheritance/dynamic resolution and CFG/DFG/non-Python/global candidate normalization remain future boundaries.

Resolved Python reference edges now pass through `graph-candidate/v1` and `normalized-graph/v1` contracts with origin, producer, support and SHA-256-bound spans. Changed/dropped candidates and issues remain auditable in memory; resolved compatibility edges are emitted only from zero-critical active output. CFG/DFG, non-Python and legacy `GraphSchemaService` outputs remain compatibility boundaries.

Capability readiness can now be calculated deterministically from declared validated evidence into the accepted five states and manifest-compatible summaries. The calculator is an internal composition boundary; the current local indexer does not yet publish its output into a production manifest/activation transaction.

Retrieval now crosses one immutable request/candidate contract with repository/index ownership, controlled retriever names, stable identities/ranks/reasons/support and a deterministic typed query classifier. Exact, lexical, symbol, endpoint, metadata, graph/context and optional local-semantic adapters feed a content-addressed `ranking-config/v1` and deterministic weighted reciprocal-rank fusion. Ranked candidates are validated against the current source snapshot before deterministic whole-span selection within an inspectable token budget; only selected blocks are persisted and projected as citations. Claim extraction, claim-support validation and evaluation thresholds remain later boundaries.

Retrieval evaluation now validates a content-addressed six-case `evaluation-case/v1` dataset and its inert synthetic source hashes/ranges, then compares exact/keyword, naive semantic top-k and deterministic hybrid methods on identical candidate observations. It exports per-case results, reviewed metric formulas, frozen run identities and semantic/report checksums. Semantic candidates are fixtures rather than provider measurements; numeric release thresholds, answer judging, load and provider-quality evidence remain later gates.

RET-004 added a loopback Ollama embedding client and a checksummed
three-repetition runner over the same EVA-001 candidate inputs. It freezes the real
`embeddinggemma` digest/dimension, exact text preprocessing, sparse/dense/weighted-RRF
configuration, per-case quality, provider timing and `/api/ps` memory. The accepted
result authorized RET-005 prototyping.

RET-005 promotes that validated adapter into a shared embedding boundary and adds a
canonical immutable `dense-embedding-index/v1` artifact. Repository/index ownership,
resolved model digest, dimension, preprocessing version and exact chunk hashes gate
loading and query use. A typed dense search adapter feeds semantic candidates only
while those identities and the provider remain compatible; missing, stale, corrupt
or unavailable state returns no semantic candidates and leaves sparse retrieval
active. Production indexing-worker composition, automatic activation/configuration,
ANN storage and production-scale load qualification remain outside this slice.

The EVA-002 `evaluation-gate/v1` boundary binds the frozen dataset, fixture, raw result and method configuration identities to reviewed smoke-only metric floors. It emits ordered fail-closed diagnostics and a content-addressed decision. The named CI job runs existing graph/readiness, incremental/equivalence, assistant and evaluation suites before applying that policy. This is deterministic regression protection, not accepted production-quality or release-threshold evidence.

The compatibility assistant now routes through immutable `assistant-config/v1`, typed request/plan/tool input/output/observation/budget contracts and an explicit exact/hybrid allowlist. Eligible direct questions stop after an exact hit; exact misses fall back once and multi-step types use hybrid retrieval directly. Tool-call/time/context budgets, cancellation, equivalent-call deduplication and safe failure diagnostics are enforced before RET-003 context selection. Multi-round repair, claim/citation validation and persistent traces remain later assistant boundaries.

Question-specific sufficiency now evaluates strong selected support, source diversity and endpoint/graph coverage. Repairable multi-step/architecture undercoverage gets at most one controlled hybrid repair inside the same owner/version and AGT-001 budgets; direct missing questions do not broaden. Deterministic and optional-provider answers must declare selected current citation IDs whose persisted scope validates exactly. Semantic entailment and evaluation thresholds remain later boundaries.

Completed assistant turns now cross one immutable privacy-safe aggregate into atomic local SQLite or production PostgreSQL persistence. Conversation messages, claims, citations, trace summaries and controlled ordered events retain repository/index ownership; replay is repository-scoped and credentials are redacted before storage. Public history endpoints, automated retention execution, authenticated-principal delivery and agent evaluation thresholds remain later boundaries.

Assistant chat requests now optionally carry bounded page/file/inclusive-line/symbol identifiers. Code Explorer derives the current active source context and Overview supplies page-only context; the composer shows and can remove the exact context before send. The backend rejects non-owned/missing/changed/out-of-range/symbol-mismatched context before retrieval and uses only validated canonical identifiers as a retrieval anchor. Graph/API context, attachments, public history replay and multi-turn memory remain absent.

Repository-owned assistant conversations now have bounded public list (50) and replay (200 messages) read models with safe not-found behavior and current-index staleness disclosure. A supplied conversation ID must already belong to the repository. Follow-up retrieval/provider intent receives at most eight recent messages within a deterministic 1,000-token estimate; conversation text remains untrusted non-evidence, and stale-index assistant text is excluded. The frontend retains the server-issued ID, deep-links and replays after refresh, and implements server-backed History and truthful New Chat. An optional native Ollama adapter validates a loopback-only origin/model/timeout, checks local model readiness and requests bounded non-streaming JSON over the existing grounded prompt; failures preserve deterministic fallback. Dense embeddings, real-model qualification, public readiness UI, pagination and retention execution remain later tasks.

The frontend now derives management/workspace identity from one React Router boundary rather than transient page state. Canonical builders preserve encoded repository, file/line, symbol, endpoint, graph, impact, search, conversation and evidence context; direct source/evidence routes restore current owned data, and invalid/missing/unusable contexts render deterministic recovery. Symbol and conversation detail read models, server-state ownership, bounded graph projections and later Phase 6 surfaces remain outside UI-001.

TanStack Query now owns repository/workspace reads, import previews, mutation results, repository-scoped conversation history and conversation-ID-scoped replay. Signal-aware API functions support superseded-query cancellation; classified bounded retries, terminal/hidden indexing polling, scoped mutation invalidation and the shared async-state projection are centralized under `frontend/src/features/server-state/`. URL identity and transient form/display state remain outside the server-state cache. Bounded graph projection and later Phase 6 feature surfaces remain outside UI-002.

The compatibility graph API now resolves one active repository version and applies deterministic server-side view/root/type/direction/depth/confidence/support filters before fixed 220-node/520-edge maxima. Additive responses disclose available/included counts, measured coverage, truncation reason, unresolved roots, expansion availability and current DTO provenance. The frontend includes normalized projection inputs in version-owned query keys, renders every returned node/edge, and provides complete/limited disclosure plus a keyboard-native relation list. Canonical opaque-version POST projection/path APIs and graph storage composition remain later boundaries.

UI-004 now presents that unchanged bounded projection through a deterministic architecture-layer canvas with SVG direction, selected-neighborhood focus, zoom/fit controls, a minimap summary, contextual relation/support/impact inspection and the complete UI-003 relation-list fallback. Overview derives a guided reading tour only from current module and important-file signals. Impact groups current compatibility results into direct, inferred and unknown and explicitly reports that historical comparison is unavailable. No new graph fact, API field, dependency or historical snapshot is synthesized by the client.

The UI-004 browser harness intercepts only owned API routes with deterministic fixtures and verifies Architecture-to-source, Graph focus/relation/reduced-motion and Impact disclosure journeys in Chromium. It also applies axe serious/critical checks and records complete Small/Medium/Large returned-projection observations; these observations do not establish an accepted release performance budget.

UI-005 now reads the existing authenticated Settings and effective-ignore responses through global TanStack Query keys and renders only the explicit non-secret fields. Evaluation retains the selected repository and active-index facts but declares interactive datasets/runs/results unavailable because those public APIs do not exist. Shared async presentation now includes typed limited and unavailable states; no backend API, provider execution, stored evaluation result or settings mutation is added.
