# Current Source Map

| Domain | Source |
| --- | --- |
| API | `backend/app/api/v1/routes/` |
| API dependency providers | `backend/app/api/dependencies.py` |
| Schemas | `backend/app/schemas/api.py` |
| Application composition/use cases | `backend/app/services/application/` |
| Ingestion | `backend/app/services/ingestion/` |
| Indexing | `backend/app/services/indexing/` |
| Parsing | `backend/app/services/parsing/` |
| Deep code analysis | `backend/app/services/code_analysis/` |
| Canonical Python adapter/IR boundary | `backend/app/services/code_analysis/adapters/python_adapter.py`, `models.py`, `pipeline.py`; current-state projection in `backend/app/services/parsing/canonical_python_parser.py` |
| Canonical Python reference resolver | `backend/app/services/code_analysis/resolver.py`; typed compatibility projection in `backend/app/services/code_analysis/cpg/emitter.py` |
| Reference-derived graph candidate normalization | `backend/app/services/code_analysis/graph_candidates.py`; in-memory audit/report state in `backend/app/services/index_models.py` |
| Deterministic capability readiness calculator | `backend/app/services/code_analysis/capability_readiness.py`; output reuses `backend/app/services/indexing/validation_service.py::CapabilityReadiness` |
| Graph/projections | `backend/app/services/graph/` |
| Typed retrieval and ranking | `backend/app/services/retrieval/contracts.py`, `query_classifier.py`, `retrievers.py`, `ranking.py`; compatibility facade in `retrieval_service.py` |
| Validated evidence selection and context budgeting | `backend/app/services/evidence/selection.py`; persistence/citation projection in `evidence_service.py` |
| Versioned retrieval evaluation | `backend/app/services/evaluation/`; immutable dataset in `evaluation/datasets/retrieval-v1/`; synthetic fixture in `tests/fixtures/retrieval_benchmark_repo/` |
| Bounded assistant, sufficiency, citation validation and trace contracts | `backend/app/services/chat/workflow_contracts.py`, `tool_registry.py`, `sufficiency.py`, `citation_validation.py`, `trace_persistence.py`; compatibility orchestration/provider boundary in `agent_workflow_service.py`, `chat_service.py`, `llm_client.py` |
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
| Frontend API/state | `frontend/src/api/`, `frontend/src/hooks/` |
| Frontend surfaces | `frontend/src/pages/`, `frontend/src/components/` |
| Tests/fixture | `tests/` |

The versioned API routes resolve domain-specific application boundaries from one
single-process composition root. `backend/app/services/codebase_service.py` remains
a compatibility adapter for direct callers; versioned routes no longer import it.

Agents use this map for targeted inspection and must not scan ignored dependency/build/runtime storage directories.

`ParserService` now routes Python through one `PythonAdapter -> IRModule` authority. `CanonicalPythonParser` is the explicit projection into the current mutable `RepositoryState`; `PythonAstParser` remains only as a deprecated import-compatible class name and contains no second AST extractor. Other language parsers still use the compatibility `LanguageParser` boundary and do not yet claim production-v1 IR capability.

The Python pipeline now retains a deterministic `resolved-reference-set/v1` artifact for imports and calls before graph compatibility output. `CPGEmitter` projects typed outcomes and no longer owns target selection. Cross-file symbol/inheritance/dynamic resolution and CFG/DFG/non-Python/global candidate normalization remain future boundaries.

Resolved Python reference edges now pass through `graph-candidate/v1` and `normalized-graph/v1` contracts with origin, producer, support and SHA-256-bound spans. Changed/dropped candidates and issues remain auditable in memory; resolved compatibility edges are emitted only from zero-critical active output. CFG/DFG, non-Python and legacy `GraphSchemaService` outputs remain compatibility boundaries.

Capability readiness can now be calculated deterministically from declared validated evidence into the accepted five states and manifest-compatible summaries. The calculator is an internal composition boundary; the current local indexer does not yet publish its output into a production manifest/activation transaction.

Retrieval now crosses one immutable request/candidate contract with repository/index ownership, controlled retriever names, stable identities/ranks/reasons/support and a deterministic typed query classifier. Exact, lexical, symbol, endpoint, metadata, graph/context and optional local-semantic adapters feed a content-addressed `ranking-config/v1` and deterministic weighted reciprocal-rank fusion. Ranked candidates are validated against the current source snapshot before deterministic whole-span selection within an inspectable token budget; only selected blocks are persisted and projected as citations. Claim extraction, claim-support validation and evaluation thresholds remain later boundaries.

Retrieval evaluation now validates a content-addressed six-case `evaluation-case/v1` dataset and its inert synthetic source hashes/ranges, then compares exact/keyword, naive semantic top-k and deterministic hybrid methods on identical candidate observations. It exports per-case results, reviewed metric formulas, frozen run identities and semantic/report checksums. Semantic candidates are fixtures rather than provider measurements; numeric release thresholds, answer judging, load and provider-quality evidence remain later gates.

The compatibility assistant now routes through immutable `assistant-config/v1`, typed request/plan/tool input/output/observation/budget contracts and an explicit exact/hybrid allowlist. Eligible direct questions stop after an exact hit; exact misses fall back once and multi-step types use hybrid retrieval directly. Tool-call/time/context budgets, cancellation, equivalent-call deduplication and safe failure diagnostics are enforced before RET-003 context selection. Multi-round repair, claim/citation validation and persistent traces remain later assistant boundaries.

Question-specific sufficiency now evaluates strong selected support, source diversity and endpoint/graph coverage. Repairable multi-step/architecture undercoverage gets at most one controlled hybrid repair inside the same owner/version and AGT-001 budgets; direct missing questions do not broaden. Deterministic and optional-provider answers must declare selected current citation IDs whose persisted scope validates exactly. Semantic entailment and evaluation thresholds remain later boundaries.

Completed assistant turns now cross one immutable privacy-safe aggregate into atomic local SQLite or production PostgreSQL persistence. Conversation messages, claims, citations, trace summaries and controlled ordered events retain repository/index ownership; replay is repository-scoped and credentials are redacted before storage. Public history endpoints, automated retention execution, authenticated-principal delivery and agent evaluation thresholds remain later boundaries.
