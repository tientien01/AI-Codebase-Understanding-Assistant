# Import and Graph Refactor Summary

## Backend

- Added streaming upload support so large ZIP/folder uploads are written in chunks instead of being fully loaded into memory.
- Raised import configuration for larger repositories and added separate limits for upload size, extracted size, ZIP entries, path depth, and compression ratio.
- Hardened ZIP handling with duplicate-path detection, nested archive skipping, path-depth checks, entry-count checks, and ZIP bomb protection.
- Added graph coverage metadata:
  - `mapped` for repository-map level areas.
  - `deep_indexed` for files/symbols/endpoints with parsed code evidence.
  - edge `evidence_level` to distinguish map-level and deep relationships.
- Added folder/project-area graph nodes so the graph can show a high-level repository map before users inspect detailed code relationships.
- Added a graph expansion endpoint as a foundation for `Analyze this area`. The MVP refreshes the project graph; this can later enqueue scoped RQ jobs.

## Frontend

- Added upload progress for ZIP/folder import using `XMLHttpRequest`.
- Updated Graph View into a simpler Project Map UI with user-facing statuses:
  - `Ready`
  - `Analyzing`
  - `Needs analysis`
  - `Skipped`
  - `Issue found`
- Added an `Analyze this area` action for graph areas that need deeper analysis.
- Updated graph side panel to show analysis coverage instead of internal graph implementation details.

## Notes

- RQ/Redis is not wired yet. The new graph expansion endpoint and job/status fields are prepared so a real background worker can replace the current synchronous refresh path.
- The UI avoids internal terms such as chunks, vectors, graph node IDs, and scope internals by default.

## Follow-up: HTML and CSS Support

- Added HTML (`.html`, `.htm`) and CSS (`.css`) to the language registry.
- HTML/CSS files are now treated as UI source files instead of unsupported files.
- Import Preview can show HTML and CSS under Detected Languages.
- Added tests so HTML/CSS support does not regress.

## Follow-up: Index Jobs UX and Job Controls

Date: 2026-07-06

### Backend

- Added controllable indexing jobs with pause, resume, and cancel support.
- Added job control endpoints:
  - `POST /api/v1/repositories/{repository_id}/index/jobs/{job_id}/pause`
  - `POST /api/v1/repositories/{repository_id}/index/jobs/{job_id}/resume`
  - `POST /api/v1/repositories/{repository_id}/index/jobs/{job_id}/cancel`
- Changed repository index API and import confirmation API to start indexing in the background, while preserving synchronous service behavior for existing tests and direct service calls.
- Added cooperative pause/cancel checks between indexing stages and between parsed files.
- Added parser hooks so indexing progress can update per file without hard-coding language-specific parser behavior.
- Cancelled or failed re-index jobs retain the previous successful index when one exists.

### Frontend

- Reworked the `Index Jobs` page to show fewer, more useful sections:
  - job status and progress;
  - generalized indexing pipeline;
  - current stage or index result;
  - diagnostics;
  - index output metrics;
  - local-time activity log;
  - job timing.
- Replaced the rigid 11-step language-specific pipeline with a generalized 8-step pipeline:
  - Prepare source
  - Scan and filter files
  - Analyze languages
  - Extract code structure
  - Create searchable chunks
  - Build relationship graph
  - Save index
  - Finalize
- Removed hard-coded UI values from the page, including the fake processing file, fixed branch name, placeholder embedding model, and simulated throughput chart.
- Removed the `Index Configuration` panel from the main page.
- Added Pause, Resume, and Cancel buttons that call the new backend job-control endpoints when a controllable job is running.
- Renamed `Live Log` to `Activity Log` and formatted timestamps in the browser's local timezone instead of showing raw UTC/ISO strings.

### Verification

- Backend tests passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_codebase_service.py tests\test_file_rules.py tests\test_service_boundaries.py`

## Follow-up: Incremental Indexing Phase 4

Date: 2026-07-10

### Backend

- Added practical incremental indexing support to the indexing pipeline.
- Preserved full indexing behavior when:
  - a repository has no previous successful index;
  - `force_reindex=true`;
  - the previous repository state is not indexed.
- Added a file-hash based incremental plan for already-indexed repositories when `force_reindex=false`.
- The incremental plan compares newly scanned files against the previous indexed file records and computes:
  - changed files;
  - deleted files;
  - unchanged files.
- Changed incremental indexing to parse only changed files instead of reparsing every indexed file.
- Removed stale records for changed and deleted files before merging newly parsed records:
  - symbols;
  - endpoints;
  - chunks;
  - graph nodes;
  - graph edges;
  - parse diagnostics;
  - failed file records.
- Reused unchanged file metadata, chunks, symbols, endpoints, and graph records across incremental runs.
- Rebuilt the project graph after merging retained and newly parsed records, so structural nodes and projections stay consistent.
- Added indexing logs that report incremental plan counts:
  - changed;
  - deleted;
  - unchanged.
- Kept cancellation and pause checks compatible with incremental parsing.

### Frontend

- Changed the default re-index action from forced full reindex to incremental reindex by sending `force_reindex=false`.

### Tests

- Added backend coverage for incremental indexing parsing only the changed file.
- Verified that newly added symbols from a changed file appear after incremental indexing.
- Verified that incremental plan logs are recorded.

### Verification

- Incremental indexing focused test passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_codebase_service.py::test_incremental_indexing_parses_only_changed_files`
- Backend graph/code-analysis tests passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_code_analysis.py`
- Frontend production build passed with:
  - `npm.cmd run build`
- Broader backend service test run still has the existing non-Phase-4 failures around fake LLM evidence sufficiency and completed-with-warnings status:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_codebase_service.py tests\test_service_boundaries.py tests\test_file_rules.py`

## Follow-up: Deterministic Hybrid Search Phase 2

Date: 2026-07-10

### Backend

- Replaced chunk-only keyword search with deterministic hybrid retrieval.
- Added `RetrievalService.hybrid_search(...)` that combines:
  - BM25-style chunk scoring;
  - lexical exact and substring matching;
  - fuzzy token matching;
  - symbol lookup;
  - endpoint lookup;
  - file lookup;
  - graph node lookup;
  - one-hop graph context boosting.
- Kept `search_chunks(...)` for chat compatibility while routing it through the new hybrid search implementation.
- Extended `SearchResultDTO` with:
  - `result_type`;
  - `retrieval_source`;
  - `matched_terms`.
- Updated `SearchService` so search evidence records preserve the retrieval source that produced the result.

### Frontend

- Extended search result types with result classification fields.
- Updated the Search page to show result type, retrieval source, and matched terms.

### Tests

- Added backend coverage for hybrid search returning endpoint, symbol, file, and fuzzy symbol matches.

### Verification

- Backend graph/code-analysis tests passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_code_analysis.py`
- Frontend production build passed with:
  - `npm.cmd run build`
- Broader backend service test run still has the existing non-Phase-2 failures around fake LLM evidence sufficiency and completed-with-warnings status:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_codebase_service.py tests\test_service_boundaries.py tests\test_file_rules.py`

## Follow-up: Graph-Based Impact Analysis Phase 3

Date: 2026-07-10

### Backend

- Added `ImpactAnalysisService` under `backend/app/services/impact/`.
- Added graph-based impact analysis that resolves targets by:
  - file path;
  - symbol name or symbol ID;
  - endpoint label or endpoint path;
  - model or schema node.
- Added bounded graph traversal for direct and indirect impact discovery.
- Added impact result grouping for:
  - direct impact;
  - indirect impact;
  - affected files;
  - affected endpoints;
  - affected tests;
  - affected symbols.
- Added deterministic risk scoring and risk levels.
- Added suggested checks based on affected endpoints, tests, and files.
- Added missing-relation notes when test or data-flow relations are unavailable.
- Added API contract models:
  - `ImpactAnalysisRequest`;
  - `ImpactTargetDTO`;
  - `ImpactItemDTO`;
  - `ImpactAnalysisResponse`.
- Added endpoint:
  - `POST /api/v1/repositories/{repository_id}/impact`
- Connected the impact service through `CodebaseService`.

### Frontend

- Replaced the placeholder Impact page with a functional target form.
- Added Impact page state and API call support in the app controller.
- Added impact result rendering for risk, direct/indirect impact, affected files, endpoints, tests, suggested checks, and known graph gaps.
- Added TypeScript types for impact analysis responses.

### Tests

- Added backend coverage for graph impact analysis finding related files, endpoints, and tests.
- Added backend coverage for unresolved impact targets returning an `unknown` risk response instead of crashing.

### Verification

- Backend graph/code-analysis tests passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_code_analysis.py`
- Frontend production build passed with:
  - `npm.cmd run build`
- Broader backend service test run still has the existing non-Phase-3 failures around fake LLM evidence sufficiency and completed-with-warnings status:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_codebase_service.py tests\test_service_boundaries.py tests\test_file_rules.py`

## Follow-up: Canonical Graph Schema Phase 1

Date: 2026-07-10

### Backend

- Extended the graph API contract with canonical metadata fields on graph nodes:
  - `start_line`;
  - `end_line`;
  - `summary`;
  - `tags`;
  - `complexity`;
  - `layer`;
  - `metadata`.
- Extended graph edges with:
  - `weight`;
  - `metadata`.
- Added `GraphSchemaService` as the single normalization boundary for graph records before storage and API use.
- Added canonical node and edge type allowlists for graph validation and future impact/retrieval work.
- Normalized graph nodes by:
  - clamping unknown node types to `unknown`;
  - normalizing Windows path separators;
  - inferring stable `summary`, `tags`, `complexity`, `layer`, and `role` values when parsers do not provide them;
  - deduplicating repeated node records by ID.
- Normalized graph edges by:
  - clamping confidence to `0..1`;
  - setting default `weight` from confidence;
  - normalizing invalid evidence levels to `inferred`;
  - preserving unknown edge type names in `metadata.original_type` while mapping them to `related_to`.
- Dropped graph edges whose source or target node is missing and records a parser diagnostic for easier debugging.
- Integrated graph normalization into `GraphService.build_graph(...)`.
- Added line ranges to graph nodes created from symbols, endpoints, JavaScript/TypeScript API calls, tree-sitter unresolved calls, CFG nodes, and DFG nodes.
- Persisted the new graph node and edge metadata fields in SQLite.
- Extended the SQLite compatibility helper so existing local databases receive the new graph columns automatically.
- Added missing SQLite compatibility coverage for `symbol_records.metadata_json`.
- Added the missing ORM field for `EndpointRecordORM.metadata_json`, matching the existing store and SQLite migration helper behavior.

### Frontend

- Extended TypeScript graph API types with the new canonical graph fields.
- Updated the Graph page details panel to show layer, complexity, line range, summary, and tags when available.

### Tests

- Added backend coverage that validates graph normalization:
  - canonical node metadata is populated;
  - edge confidence is clamped;
  - edge weight is populated;
  - invalid dangling edges are dropped;
  - graph normalization diagnostics are recorded.

### Verification

- Backend graph/code-analysis tests passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_code_analysis.py`
- Frontend production build passed with:
  - `npm.cmd run build`
- Broader backend service test run currently has pre-existing/non-Phase-1 failures:
  - `tests/test_codebase_service.py::test_service_indexes_fixture_and_answers_with_evidence`
  - `tests/test_codebase_service.py::test_force_reindex_replaces_index_records_without_duplicates`
  - `tests/test_codebase_service.py::test_ask_with_selected_evidence_requires_valid_evidence`
- The broader run command was:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_codebase_service.py tests\test_service_boundaries.py tests\test_file_rules.py`

## Follow-up: Python Code Analysis Pipeline Phase 1-6

Date: 2026-07-07

### Backend

- Added a new `backend/app/services/code_analysis/` pipeline for language-independent code analysis foundations.
- Added stable ID utilities for files, symbols, chunks, graph nodes, graph edges, and AST-derived nodes.
- Added Universal IR models for modules, imports, classes, functions, parameters, statements, expressions, endpoints, CFG, DFG, and CPG results.
- Added a Python AST adapter that maps Python source into the Universal IR instead of emitting repository records directly.
- Added a generic CFG builder that operates on IR functions and emits control-flow nodes and edges.
- Added a generic DFG builder that operates on IR functions and emits parameter, definition, use, computed-from, and return-flow relations.
- Added a CPG emitter that converts IR + CFG + DFG output back into the existing repository state model:
  - symbols;
  - endpoints;
  - chunks;
  - graph nodes;
  - graph edges.
- Integrated the new code analysis pipeline into the existing Python parser with fallback to the previous AST parser behavior if the new pipeline fails.
- Changed chunk IDs to deterministic stable IDs instead of random UUID-based IDs.
- Preserved compatibility with existing import graph behavior by emitting both base module imports and detailed imported-symbol module edges.

### Tests

- Added `tests/test_code_analysis.py`.
- Added coverage for stable Python symbol IDs when line numbers shift.
- Added coverage for emitted CFG branch and return edges.
- Added coverage for emitted DFG assignment and return-flow edges.

### Verification

- Backend tests passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_code_analysis.py tests\test_service_boundaries.py tests\test_codebase_service.py tests\test_file_rules.py`

## Follow-up: Graph Projection and Analysis Views

Date: 2026-07-07

### Backend

- Added `GraphProjectionService` to create bounded graph views instead of returning only the raw repository graph.
- Added graph projections for:
  - project map;
  - dependency graph;
  - API flow;
  - function flow;
  - data flow.
- Added graph view endpoints:
  - `GET /repositories/{repository_id}/graph/project-map`
  - `GET /repositories/{repository_id}/graph/dependencies`
  - `GET /repositories/{repository_id}/graph/api-flow`
  - `GET /repositories/{repository_id}/graph/function-flow`
  - `GET /repositories/{repository_id}/graph/data-flow`
- Added a tree-sitter adapter base with shared helpers for future language adapters.
- Added lightweight parse diagnostics storage on `RepositoryState` so parser diagnostics can be carried through indexing state.

### Frontend

- Added graph view state and projection loading to the app controller.
- Updated the Graph page to switch between Project Map, Dependencies, API Flow, Function Flow, and Data Flow.
- Kept the existing graph UI lightweight while moving data selection to backend graph projections.

### Tests

- Added graph projection coverage to `tests/test_code_analysis.py`.

### Verification

- Backend tests passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_code_analysis.py tests\test_service_boundaries.py tests\test_codebase_service.py tests\test_file_rules.py`
- Frontend production build passed with:
  - `npm.cmd run build`

## Follow-up: Automatic Import Preview

Date: 2026-07-07

### Backend

- Added GitHub URL import-session support:
  - `POST /api/v1/import-sessions/github`
  - accepts a public HTTPS GitHub repository URL;
  - clones the repository shallowly into the import-session source folder;
  - removes the cloned `.git` directory before preview/indexing;
  - reuses the existing preview scan, security filtering, duplicate detection, and confirm/indexing flow.
- Added `GitHubImportRequest` to the API schema.
- Added `CodebaseService.create_github_import_session(...)` so the route uses the same facade pattern as ZIP and folder imports.
- Validates GitHub URLs before cloning and rejects non-GitHub or malformed URLs with `INVALID_GITHUB_URL`.

### Frontend

- Import Preview is now prepared automatically:
  - selecting a local folder starts upload and preview creation immediately;
  - selecting a ZIP starts upload and preview creation immediately;
  - pasting a valid GitHub URL starts preview creation after a short debounce.
- Removed the need to click a manual Preview button.
- The primary import action is disabled until preview is ready and then becomes `Start Indexing`.
- Added a lightweight `Preparing preview...` status in the preview panel.
- Changed the default GitHub URL field from a fake valid URL to an empty field so opening the GitHub tab does not accidentally trigger a clone.

### Tests

- Added backend coverage for GitHub import session preview by mocking the clone step, avoiding network access in tests.
- Added backend coverage for rejecting non-GitHub URLs.

### Verification

- Backend tests passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_codebase_service.py tests\test_file_rules.py tests\test_service_boundaries.py`
- Frontend production build passed with:
  - `npm.cmd run build`
- Frontend production build passed with:
  - `npm.cmd run build`

## Follow-up: Projects Page Focus and CSS Split

Date: 2026-07-06

### Frontend

- Removed the `Project Summary` side panel from the `Projects` page to reduce duplicated dashboard-style information.
- Added icons to the project card stats row:
  - files indexed;
  - endpoints;
  - symbols;
  - last indexed.
- Reworked `Next Actions` into state-aware action cards with icon, priority tone, count, description, and clear CTA.
- Kept actions driven by repository status instead of hard-coded static rows.
- Split Projects-specific styles from `frontend/src/App.css` into `frontend/src/pages/management/ProjectsPage.css` so the global stylesheet stays focused on shared layout and components.

### Verification

- Frontend production build passed with:
  - `npm.cmd run build`

## Follow-up: Import Preview Optimization

Date: 2026-07-07

### Backend

- Reduced duplicate filesystem work in Import Preview by extending scanner diagnostics with one-pass summary fields:
  - total files;
  - total repository size;
  - supported source size;
  - language file counts.
- Changed Import Preview to reuse scanner summary instead of running extra `rglob()` passes for size, total files, and language statistics.
- Cached the generated preview response inside the in-memory import session so repeated `GET /import-sessions/{id}/preview` calls do not rescan the uploaded source.
- Kept duplicate candidates dynamic when serving a cached preview, so newly imported repositories can still appear in duplicate checks.
- Added a project fingerprint based on sorted indexed file paths, sizes, and content hashes.
- Improved duplicate detection with `same_fingerprint`, which is stronger than matching by project name or source label.
- Replaced the coarse `supported_files // 25` index-time estimate with a file-count, supported-size, and language-weighted estimate.
- Returned the actual session status `preview_ready` from import-session creation responses instead of the generic `created` status.

### Tests

- Updated import-session tests to expect `preview_ready`.
- Added coverage for cached preview reuse after the first scan.
- Added coverage for duplicate detection by project fingerprint.

### Verification

- Backend tests passed with:
  - `backend\.venv\Scripts\python.exe -m pytest tests\test_codebase_service.py tests\test_file_rules.py tests\test_service_boundaries.py`
