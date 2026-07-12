# Current Implementation Delta

## Document Purpose

This document records the current source-code implementation compared with the production-oriented documentation in `docs/00` through `docs/18`.

The older documents describe the target product. The current codebase is an MVP that already implements several core workflows, plus some pragmatic local-first features that are not fully reflected in the production docs yet.

Use this document as the current implementation snapshot before updating the full production docs.

## Source Layout

The repository does not use a root-level `src` directory for all application code.

Current source layout:

- `backend/app` contains the FastAPI backend.
- `frontend/src` contains the React/Vite frontend.
- `tests` contains backend tests and fixtures.
- `storage` contains local runtime data such as SQLite metadata, uploaded sources, and indexed repositories.

Important constraint:

- Secret and credential files are intentionally not part of implementation analysis.

## Current Backend Scope

The backend is implemented as a local-first FastAPI application.

Implemented core areas:

- Repository import and management.
- Import sessions for ZIP, folder upload, and public GitHub URL import.
- Import preview with detected languages, file statistics, ignore summaries, warnings, duplicate candidates, and activity logs.
- Repository indexing with job status.
- Index job history and diagnostics.
- Pause, resume, and cancel controls for running index jobs.
- File scanning and safe filtering.
- Python, JavaScript, TypeScript, HTML, CSS, Markdown, config, Docker, and tree-sitter-backed source parsing.
- Chunk generation.
- Graph construction and graph projections.
- Overview and reading path.
- File tree and file content APIs.
- Symbol and endpoint listing.
- Hybrid search.
- Evidence creation and validation.
- Grounded chat fallback.
- Impact analysis over the graph.
- Basic settings read APIs.

The main API implementation is currently concentrated in one route module:

- `backend/app/api/v1/routes/repositories.py`

## API Differences From Production Contract

The production API contract in `04_api_contract.md` is broader than the current backend.

### Implemented API Areas

Current implemented API groups include:

- Health:
  - `GET /health`
- Import sessions:
  - `POST /api/v1/import-sessions/upload-zip`
  - `POST /api/v1/import-sessions/upload-folder`
  - `POST /api/v1/import-sessions/github`
  - `GET /api/v1/import-sessions/{import_session_id}/preview`
  - `POST /api/v1/import-sessions/{import_session_id}/confirm`
  - `DELETE /api/v1/import-sessions/{import_session_id}`
- Repositories:
  - `GET /api/v1/repositories`
  - `DELETE /api/v1/repositories/{repository_id}`
  - `POST /api/v1/repositories/bulk-delete`
  - legacy direct upload endpoints:
    - `POST /api/v1/repositories/upload`
    - `POST /api/v1/repositories/upload-folder`
- Indexing:
  - `POST /api/v1/repositories/{repository_id}/index`
  - `GET /api/v1/repositories/{repository_id}/index/status`
  - `GET /api/v1/repositories/{repository_id}/index/jobs`
  - `POST /api/v1/repositories/{repository_id}/index/jobs/{job_id}/pause`
  - `POST /api/v1/repositories/{repository_id}/index/jobs/{job_id}/resume`
  - `POST /api/v1/repositories/{repository_id}/index/jobs/{job_id}/cancel`
  - `GET /api/v1/repositories/{repository_id}/index/jobs/{job_id}/warnings`
  - `GET /api/v1/repositories/{repository_id}/index/jobs/{job_id}/skipped-files`
  - `GET /api/v1/repositories/{repository_id}/index/jobs/{job_id}/failed-files`
- Workspace:
  - `GET /api/v1/repositories/{repository_id}/staleness`
  - `GET /api/v1/repositories/{repository_id}/overview`
  - `GET /api/v1/repositories/{repository_id}/reading-path`
  - `GET /api/v1/repositories/{repository_id}/symbols`
  - `GET /api/v1/repositories/{repository_id}/api/endpoints`
  - `GET /api/v1/repositories/{repository_id}/files/tree`
  - `GET /api/v1/repositories/{repository_id}/files/content`
- Assistant and evidence:
  - `POST /api/v1/repositories/{repository_id}/chat`
  - `GET /api/v1/repositories/{repository_id}/evidence/{evidence_id}`
  - `POST /api/v1/repositories/{repository_id}/evidence/validate`
  - `POST /api/v1/repositories/{repository_id}/search/ask-with-evidence`
- Search:
  - `GET /api/v1/repositories/{repository_id}/search`
- Graph:
  - `GET /api/v1/repositories/{repository_id}/graph`
  - `GET /api/v1/repositories/{repository_id}/graph/project-map`
  - `GET /api/v1/repositories/{repository_id}/graph/dependencies`
  - `GET /api/v1/repositories/{repository_id}/graph/api-flow`
  - `GET /api/v1/repositories/{repository_id}/graph/function-flow`
  - `GET /api/v1/repositories/{repository_id}/graph/data-flow`
  - `POST /api/v1/repositories/{repository_id}/graph/expand`
- Impact:
  - `POST /api/v1/repositories/{repository_id}/impact`
- Settings:
  - `GET /api/v1/settings`
  - `GET /api/v1/settings/ignore-patterns`

### Missing Or Partial Production API Areas

Current backend does not yet implement the full production contract for:

- Repository detail endpoint:
  - `GET /repositories/{repository_id}`
- Repository sync:
  - `POST /repositories/{repository_id}/sync`
- Individual indexing job detail:
  - `GET /repositories/{repository_id}/index/jobs/{job_id}`
- File detail by file ID:
  - `GET /repositories/{repository_id}/files/{file_id}`
  - `GET /repositories/{repository_id}/files/{file_id}/symbols`
- Symbol detail and references:
  - `GET /repositories/{repository_id}/symbols/{symbol_id}`
  - `GET /repositories/{repository_id}/symbols/{symbol_id}/references`
- Conversation persistence:
  - `GET /repositories/{repository_id}/conversations`
  - `POST /repositories/{repository_id}/conversations`
  - `GET /repositories/{repository_id}/conversations/{conversation_id}`
  - `DELETE /repositories/{repository_id}/conversations/{conversation_id}`
- Agent trace API:
  - `GET /repositories/{repository_id}/messages/{message_id}/agent-trace`
- Graph detail and path APIs:
  - `GET /repositories/{repository_id}/graph/nodes/{node_id}`
  - `GET /repositories/{repository_id}/graph/paths`
- API explorer detail and flow endpoints:
  - `GET /repositories/{repository_id}/api/endpoints/{endpoint_id}`
  - `GET /repositories/{repository_id}/api/endpoints/{endpoint_id}/flow`
- Related tests endpoint:
  - `GET /repositories/{repository_id}/tests/related`
- Evaluation APIs:
  - `GET /evaluation/datasets`
  - `POST /evaluation/datasets`
  - `GET /evaluation/datasets/{dataset_id}`
  - `POST /evaluation/runs`
  - `GET /evaluation/runs/{run_id}`
  - `GET /evaluation/runs/{run_id}/results`
- Settings mutation and provider testing:
  - `PATCH /settings`
  - `PATCH /settings/ignore-patterns`
  - `GET /settings/providers`
  - `PATCH /settings/providers`
  - `POST /settings/providers/test`

## Data Model Differences

The production data model in `03_data_model.md` includes many entities that are not yet persisted in the current backend.

Current SQLite ORM tables:

- `repositories`
- `indexing_jobs`
- `file_records`
- `symbol_records`
- `endpoint_records`
- `chunk_records`
- `graph_nodes`
- `graph_edges`
- `evidence`

Not yet implemented as first-class persisted tables:

- `RepositorySource`
- `ImportSession`
- `ParsedImport`
- `ApiCallRecord`
- `ProjectMentalModel`
- `Conversation`
- `Message`
- `EvaluationDataset`
- `EvaluationQuestion`
- `EvaluationGroundTruth`
- `EvaluationRun`
- `EvaluationResult`
- `AppSetting`

Current implication:

- Import sessions exist as service-level workflow records, but are not represented by the production data model table set.
- Chat is handled as request/response with evidence, but conversation history is not production-persisted.
- Evaluation pages and docs exist, but evaluation backend persistence is not implemented.
- Settings are read from application configuration and service defaults, not from a full mutable settings table.

## Import And Preview Differences

Current implementation supports:

- ZIP upload import sessions.
- Browser folder upload import sessions.
- Public GitHub URL import sessions.
- Automatic preview creation from the frontend.
- Preview response caching inside the import session flow.
- Duplicate detection using project fingerprint.
- Upload progress on the frontend.
- Streaming upload writes for large ZIP/folder uploads.
- ZIP safety hardening:
  - duplicate path detection;
  - nested archive skipping;
  - path depth checks;
  - entry count checks;
  - compression ratio checks;
  - extracted size limits.

Production docs describe this area at a broader product level. The current implementation is more concrete in some local import behaviors, especially upload streaming, preview caching, and fingerprint duplicate detection.

Current limitations:

- GitHub import uses shallow clone for public HTTPS GitHub URLs.
- GitHub sync is not implemented.
- GitHub OAuth and private repository access are not implemented.
- Import session persistence is not production-grade.

## Indexing Pipeline Differences

The production docs describe a detailed indexing pipeline. The current implementation uses a compact practical pipeline:

1. `scan_repository_files`
2. `apply_ignore_rules`
3. `parse_source_code`
4. `create_chunks`
5. `build_code_graph`
6. `finalize`

Important implementation differences:

- Indexing can run in a background thread.
- RQ/Redis is not wired yet.
- Running jobs can be paused, resumed, or cancelled.
- Pause/cancel checks are cooperative between stages and parsed files.
- Re-index defaults to incremental behavior from the frontend.
- Incremental indexing compares file hashes against the previous successful index.
- Incremental indexing parses only changed files.
- Deleted and changed file records are removed before merging newly parsed records.
- Unchanged file metadata, chunks, symbols, endpoints, and graph records are reused.
- Failed or cancelled re-index jobs retain the previous successful index when possible.
- Intentional scanner skips no longer force `completed_with_warnings`.

Current limitations:

- Background indexing uses process-local thread controls, so job controls are not durable across process restarts.
- There is no distributed worker queue yet.
- Indexing job detail exists through list/status/diagnostic endpoints, but not the exact production job-detail endpoint.

## Parser And Code Intelligence Differences

Current parser support includes:

- Python AST parser.
- New Python code analysis pipeline using Universal IR foundations.
- CFG builder for Python functions.
- DFG builder for Python functions.
- CPG emitter that converts IR, CFG, and DFG output into current repository records.
- Stable IDs for files, symbols, chunks, graph nodes, graph edges, and AST-derived nodes.
- JavaScript and TypeScript parser.
- Tree-sitter parser fallback for supported source languages.
- Source fallback parser for broad source files.
- Markdown, config, and Docker fallback parsing.
- HTML and CSS recognized as UI source files.

Current supported language registry includes:

- Python
- HTML
- CSS
- JavaScript
- TypeScript
- Go
- Rust
- Java
- Kotlin
- C
- C++
- C#
- PHP
- Ruby
- Swift
- Markdown
- Docker
- Config files

Important differences from production docs:

- Python analysis is the deepest current parser path.
- JavaScript/TypeScript analysis exists, but is not yet as deep as the Python IR/CFG/DFG path.
- Other source languages depend mostly on tree-sitter or fallback parsing.
- Parser output is adapted into the current repository state model, not persisted exactly as the full production parser output schema.
- Parse diagnostics are carried in repository state and indexing diagnostics, but not yet modeled as a full production diagnostic subsystem.

## Graph Differences

Current graph implementation includes:

- Repository root, folder, file, symbol, endpoint, and relationship graph nodes.
- Coverage metadata:
  - `mapped`
  - `deep_indexed`
- Edge evidence levels.
- Canonical graph schema normalization.
- Node metadata:
  - line ranges;
  - summary;
  - tags;
  - complexity;
  - layer;
  - role;
  - metadata.
- Edge metadata:
  - confidence;
  - evidence level;
  - weight;
  - metadata.
- Graph projections:
  - project map;
  - dependencies;
  - API flow;
  - function flow;
  - data flow.
- Graph expansion endpoint foundation for analyzing an area.

Important differences from production docs:

- The frontend Graph View is currently closer to a practical Project Map and projection viewer.
- Graph path and graph node detail APIs from the production contract are not implemented.
- Graph expansion currently refreshes or prepares scoped analysis behavior, but does not enqueue real background scoped RQ jobs.
- Graph complexity is bounded and projection-based rather than a full interactive graph analysis product.

## Retrieval And Search Differences

Production docs describe provider-backed retrieval with embeddings and vector stores such as ChromaDB.

Current implementation is local-first and deterministic:

- Hybrid search combines:
  - BM25-style chunk scoring;
  - exact lexical matching;
  - substring matching;
  - fuzzy token matching;
  - symbol lookup;
  - endpoint lookup;
  - file lookup;
  - graph node lookup;
  - one-hop graph context boosting.
- Local sparse-vector retrieval is implemented without external dependencies.
- Local vector search builds token and subtoken vectors from:
  - file paths;
  - symbol names;
  - chunk types;
  - chunk content;
  - semantic summary chunks.
- Search result DTOs include:
  - `result_type`;
  - `retrieval_source`;
  - `matched_terms`.
- `semantic_vector` is a current retrieval source.

Important differences:

- ChromaDB is listed in dependencies but the current active retrieval path does not require ChromaDB.
- OpenAI embeddings are not required for the current MVP.
- The implementation favors deterministic behavior for local demos and tests.

## Semantic Enrichment Differences

The current code includes deterministic semantic enrichment after graph construction.

Implemented behavior:

- Adds summaries, tags, architectural layers, complexity labels, and enrichment metadata to graph nodes.
- Adds heuristic file summaries.
- Adds `semantic_summary` chunks.
- Re-normalizes the graph after enrichment.
- Updates chunk totals after enrichment creates additional chunks.

This is a pragmatic local implementation of semantic context. It does not depend on LLM-generated summaries.

## Assistant And Agent Workflow Differences

Production docs describe an advanced agentic AI layer with planner, tool routing, verification, traces, and multi-step investigation.

Current implementation uses a deterministic workflow:

- Classifies the question.
- Builds a retrieval plan.
- Runs hybrid search and semantic-vector retrieval.
- Adds graph context for API, flow, and impact questions.
- Converts retrieved chunks into citations.
- Checks basic evidence sufficiency.
- Produces a deterministic grounded fallback answer.
- Optionally uses configured LLM generation if provider settings are available.

Important differences:

- LangGraph is not wired.
- Multi-agent verification is not implemented.
- Agent trace persistence and trace API are not implemented.
- Conversation and message history are not persisted in the production data model.
- Evidence sufficiency checks are intentionally simple and deterministic.

## Evidence And Citation Differences

Current implementation supports:

- Evidence records generated from search/chat citations.
- Evidence lookup by evidence ID.
- Evidence validation by ID list.
- Stale evidence marking after new index versions.
- Retrieval source tracking.

Current limitations:

- Citation lifecycle is simpler than production docs.
- Evidence validation checks current indexed evidence, but does not implement a full independent verifier agent.
- Stale citation UX exists only through current API/frontend behavior, not full production workflows.

## Impact Analysis Differences

Current implementation includes graph-based impact analysis.

Implemented behavior:

- Resolves targets by:
  - file path;
  - symbol name;
  - symbol ID;
  - endpoint label;
  - endpoint path;
  - model or schema node.
- Performs bounded graph traversal.
- Groups impact into:
  - direct impact;
  - indirect impact;
  - affected files;
  - affected endpoints;
  - affected tests;
  - affected symbols.
- Computes deterministic risk score and risk level.
- Returns suggested checks.
- Reports missing graph relation notes when test or data-flow relations are unavailable.

Important differences:

- Impact analysis is implemented earlier than some other production areas.
- Related tests endpoint from the API contract is not implemented separately.
- Accuracy depends on graph completeness, which is still strongest for Python and current parser-supported relationships.

## Frontend Differences

The frontend has a React/Vite workspace aligned with the UX docs, but several pages are MVP-level.

Implemented frontend pages:

- Projects
- Import
- Index Jobs
- Workspace Overview
- Code Explorer
- Graph View
- API Explorer
- AI Assistant
- Impact Analysis
- Search
- Evidence Viewer
- Evaluation
- Settings

Current frontend implementation details:

- Import preview starts automatically after selecting ZIP/folder or entering a valid GitHub URL.
- Upload progress is shown for ZIP and folder import.
- Projects page focuses on repository status and next actions.
- Index Jobs page shows practical job status, progress, diagnostics, output metrics, activity logs, and job controls.
- Code Explorer loads real file tree and file content.
- Graph View supports projection switching.
- Impact page has a functional target form and renders backend impact results.
- Search page renders result type, retrieval source, and matched terms.
- Evidence page can open citations from chat/search.

MVP or placeholder areas:

- Evaluation page does not have a real backend evaluation runner.
- Settings page displays static/current config information but cannot mutate provider or ignore settings.
- API Explorer is based on overview endpoint data, not full endpoint detail and runtime flow APIs.
- Code Explorer does not yet support full jump-to-definition and references.
- Graph visualization is lightweight and bounded, not a full production graph canvas.

## Settings And Provider Differences

Production docs describe configurable provider settings and provider test APIs.

Current implementation:

- Reads configuration from Pydantic settings and environment.
- Exposes basic settings through `GET /api/v1/settings`.
- Exposes effective ignore patterns through `GET /api/v1/settings/ignore-patterns`.
- Uses fake/local defaults:
  - fake LLM provider by default;
  - fake embedding provider by default;
  - local vector store provider by default.

Current limitations:

- No settings persistence table.
- No settings mutation endpoint.
- No provider test endpoint.
- No full provider abstraction UI workflow.

## Storage Differences

Current storage behavior:

- SQLite database defaults to `storage/app.db`.
- Repository source storage defaults to `storage/repositories`.
- Upload storage defaults to `storage/uploads`.
- Index and parse debug artifacts may be written under local storage paths.

Important differences:

- Alembic is listed as a dependency, but full migration management is not production-grade yet.
- The current SQLite compatibility path is pragmatic for MVP evolution.
- Vector store persistence is not implemented as a production Chroma/Qdrant-style storage layer.
- Evaluation artifacts storage is not implemented.

## Security Differences

Implemented security-related behavior:

- Secret-like files are ignored by file rules.
- `.env`, credential, key, and PEM patterns are included in effective ignore patterns.
- ZIP import safety checks exist.
- Optional API auth token support exists.
- The system is local-first by default.

Current limitations:

- No production authentication or user management.
- No project access control.
- No GitHub OAuth/private repository access.
- No full secret scanning report workflow beyond filtering and warnings.

## Testing Differences

Current tests cover the implemented MVP areas, including:

- Codebase service behavior.
- File rules and scanning.
- Service boundaries.
- Code analysis pipeline.
- Hybrid retrieval and semantic-vector behavior.
- Incremental indexing behavior.
- Graph normalization and projection behavior.
- Impact analysis behavior.
- Import preview caching and duplicate fingerprint behavior.

Production docs describe a broader test plan that is not fully implemented, especially:

- Evaluation datasets and runs.
- Frontend component and E2E smoke coverage.
- Provider failure integration tests.
- Full conversation and citation lifecycle tests.
- Settings/provider mutation tests.

## Major Additions Not Fully Reflected In Older Docs

The current source has several capabilities that should be promoted into the main docs during the next documentation update:

- Streaming uploads for ZIP/folder import.
- Automatic import preview.
- Preview caching.
- Project fingerprint duplicate detection.
- Background indexing with pause/resume/cancel.
- Incremental re-indexing by file hash.
- Previous-index retention on failed or cancelled re-index.
- Canonical graph schema normalization.
- Graph projections.
- Graph area expansion foundation.
- Python IR/CFG/DFG/CPG analysis pipeline.
- Deterministic semantic enrichment.
- Deterministic hybrid search.
- Local sparse-vector retrieval.
- Deterministic agent workflow fallback.
- Graph-based impact analysis.
- HTML and CSS source support.

## Major Production Features Still Pending

The most important production gaps are:

- Durable background worker queue such as RQ/Redis.
- Full database migration discipline.
- Full production data model.
- Conversation and message persistence.
- Agent trace persistence and trace API.
- LangGraph or equivalent tool-orchestration workflow.
- Independent verification agent.
- Provider settings mutation and provider tests.
- Real embedding/vector store integration.
- GitHub sync and private repository import.
- Production authentication and project access control.
- Full API explorer endpoint detail and runtime flow.
- Symbol references and graph path APIs.
- Evaluation backend datasets, runs, metrics, and dashboard integration.
- Stronger frontend tests and E2E smoke flows.

## Current Product Position

The current implementation is best described as a local-first MVP with strong code-understanding foundations.

It already supports the main demo loop:

1. Import a repository.
2. Preview repository contents.
3. Confirm and index.
4. Browse overview, files, symbols, endpoints, graph, and search results.
5. Ask grounded questions with citations.
6. Open evidence.
7. Run graph-based impact analysis.

It is not yet the full production product described in the main docs. The biggest architectural difference is that the current code favors deterministic local behavior over external LLM, embedding, vector database, worker, and auth infrastructure.

