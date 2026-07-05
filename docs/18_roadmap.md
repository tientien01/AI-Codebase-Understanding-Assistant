# AI Codebase Assistant Roadmap

## Document Purpose

This roadmap translates the product proposal, feature catalog, architecture, API contract, indexing pipeline, agent workflow, evidence rules, frontend UX, evaluation plan, storage design, parser schema, error handling, and testing plan into an implementation path.

The roadmap is product-driven, not only code-driven. Each feature is tied to:

- related use cases from `01_feature_catalog.md`;
- backend/API/service work;
- frontend workspace surface;
- recommended development tech stack;
- definition of done.

The goal is to build a portfolio-quality AI engineering project that demonstrates code intelligence, hybrid retrieval, graph reasoning, agentic workflow, evidence-grounded answers, and a polished developer workspace.

## Roadmap Principles

- Build deterministic code intelligence before relying on LLM reasoning.
- Keep routes thin and services focused.
- Treat evidence and citations as first-class product objects.
- Do not mark semantic, vector, graph, agentic, impact, or evaluation features as complete until the backend behavior exists.
- Every implemented product feature must have a visible frontend surface or an explicit `In development` state.
- Never index, embed, log, or display real secret files.
- Use local-first defaults, but choose tech that can scale to a production-ready direction.

## Target Tech Stack

### Core Stack

| Area | Recommended stack | Purpose |
| --- | --- | --- |
| Backend API | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 | Repository APIs, import sessions, indexing status, search, chat, evidence, settings |
| Persistence | SQLAlchemy 2.0, Alembic, SQLite first, PostgreSQL-ready schema | Metadata, jobs, parser outputs, evidence, conversations, evaluation |
| Frontend | React, TypeScript, Vite, TanStack Query, React Router | Developer workspace, job polling, deep links, API state management |
| Code viewer | Monaco Editor | File detail, line numbers, citation highlighting |
| Graph UI | React Flow or Cytoscape.js | Dependency graph, API flow, impact graph |
| Icons/UI | lucide-react, consistent workspace components | Developer-tool UI controls |
| Testing | pytest, pytest-asyncio, pytest-cov, ESLint, TypeScript build | Regression safety and demo readiness |
| DevOps | Docker, Docker Compose, GitHub Actions | Reproducible local demo and CI |

### AI and Retrieval Stack

| Area | Recommended stack | Purpose |
| --- | --- | --- |
| LLM | OpenAI API or Azure OpenAI | Grounded answer generation, planning support, explanation |
| Agent workflow | LangGraph over testable service functions | Planner, tool router, evidence verifier, answer generator |
| Embeddings | OpenAI embeddings plus sentence-transformers/BGE local option | Semantic retrieval |
| Vector store | ChromaDB for local demo, Qdrant or pgvector as production option | Persistent vector search |
| Reranking | BGE reranker or Cohere Rerank optional | Improve evidence ranking |
| Evaluation | Custom benchmark runner, optional RAGAS/DeepEval | Citation accuracy, groundedness, hallucination rate |

### Code Intelligence Stack

| Area | Recommended stack | Purpose |
| --- | --- | --- |
| Python parser | Python `ast`, optional LibCST/astroid later | Functions, classes, imports, calls, FastAPI routes, models |
| JS/TS parser | Tree-sitter preferred, regex fallback only for MVP | Imports, exports, React components, API calls, tests |
| Config/docs parsers | PyYAML, tomli, JSON parser, Markdown parser | Config variables, Docker/compose, docs sections |
| Graph analysis | NetworkX first, optional Neo4j later | Graph traversal, centrality, impact analysis |

## Current Baseline

The current implementation already supports the baseline of local repository understanding:

- folder and ZIP import sessions;
- preview diagnostics for supported/skipped/security-warning files;
- repository records and managed storage;
- synchronous indexing;
- file scanning and ignore rules;
- Python/JS/TS/Markdown/config parsing at MVP depth;
- chunks, basic graph records, endpoint detection, and keyword retrieval;
- evidence persistence and citation validation;
- file tree/content, overview, reading path, symbols, endpoints, settings, staleness, indexing diagnostics APIs;
- frontend page shells and import/index/search/chat wiring for MVP flows.

The implementation should now evolve from MVP behavior into the full product described in the docs.

## Phase 1 - Core Local Codebase Workspace

Goal: make the local-first product reliable and demo-ready for folder/ZIP repositories.

### 1.1 Repository Import, Preview, and Duplicate Handling

| Field | Details |
| --- | --- |
| Use cases | U001, U002, U003 |
| Backend/services | `ImportSessionService`, `UploadService`, `ArchiveService`, `RepositoryService`, duplicate detector |
| API | `POST /import-sessions/upload-zip`, `POST /import-sessions/upload-folder`, `GET /import-sessions/{id}/preview`, `POST /import-sessions/{id}/confirm`, `DELETE /import-sessions/{id}` |
| Frontend | Project Dashboard, Import Repository Wizard, Import Preview |
| UI behavior | Show detected stack, file statistics, skipped summary, security warnings, duplicate candidates, and Start Indexing action |
| Tech stack | FastAPI multipart upload, Pydantic DTOs, local filesystem storage, TanStack Query mutation flow |
| Definition of done | User can upload ZIP/folder, review preview, cancel safely, confirm indexing, and understand duplicates without seeing internal storage paths |

### 1.2 Project Dashboard and Repository Management

| Field | Details |
| --- | --- |
| Use cases | U002, U003, U028 |
| Backend/services | `RepositoryService`, `RepositoryStore`, storage cleanup |
| API | `GET /repositories`, `GET /repositories/{id}`, `DELETE /repositories/{id}`, `POST /repositories/{id}/index` |
| Frontend | Project Dashboard |
| UI behavior | Cards/table with name, source label, status, detected stack, file count, endpoint count, last indexed time, actions |
| Tech stack | React, TypeScript, TanStack Query, status badges, confirmation modal |
| Definition of done | User can open, re-index, delete, and filter projects; delete does not remove files outside managed storage |

### 1.3 Indexing Status and Diagnostics

| Field | Details |
| --- | --- |
| Use cases | U006, U007, U008, U009 |
| Backend/services | `IndexingService`, `IndexingJobService`, scanner diagnostics, parser warnings, stale detector |
| API | `GET /repositories/{id}/index/status`, `GET /repositories/{id}/index/jobs`, `GET /repositories/{id}/index/jobs/{job_id}/warnings`, `skipped-files`, `failed-files`, `GET /repositories/{id}/staleness` |
| Frontend | Indexing Status page, project card status, workspace stale banner |
| UI behavior | Pipeline progress, current step, logs, warnings, skipped files, failed files, retry, open workspace |
| Tech stack | FastAPI, SQLAlchemy job records, TanStack Query polling |
| Definition of done | Re-index is repeatable, diagnostics are visible, partial parser failures do not hide successful indexing |

### 1.4 Workspace Overview and Reading Path

| Field | Details |
| --- | --- |
| Use cases | U010, U013 |
| Backend/services | `RepositoryService`, future `ProjectMentalModelService` |
| API | `GET /repositories/{id}/overview`, `GET /repositories/{id}/reading-path` |
| Frontend | Workspace Overview |
| UI behavior | Detected stack, important files, modules, endpoints, docs gaps, risk areas, suggested reading path |
| Tech stack | Pydantic response schemas, metadata heuristics, React workspace layout |
| Definition of done | New developer can identify what the project is, where to start, and which evidence/signals support recommendations |

### 1.5 Code Explorer and Evidence Viewer

| Field | Details |
| --- | --- |
| Use cases | U011, U012, U015 |
| Backend/services | `FileService`, `EvidenceService`, symbol detail service |
| API | `GET /files/tree`, `GET /files/content`, `GET /files/{file_id}`, `GET /files/{file_id}/symbols`, `GET /symbols/{symbol_id}`, `GET /evidence/{evidence_id}`, `POST /evidence/validate` |
| Frontend | Code Explorer, Evidence Viewer, right evidence panel |
| UI behavior | File tree, code viewer, line numbers, symbol outline, citation chips, stale citation warning |
| Tech stack | Monaco Editor, React Router deep links, TanStack Query, Pydantic evidence DTOs |
| Definition of done | Search/chat/API citations can open exact files and line ranges, and stale evidence is visible |

## Phase 2 - Strong Code Intelligence Layer

Goal: turn indexing from simple metadata extraction into a normalized code intelligence layer that powers graph, API, search, and agent tools.

### 2.1 Normalized Parser Output

| Field | Details |
| --- | --- |
| Use cases | U006, U010, U011, U012, U019, U021 |
| Backend/services | `ParserService`, language parser modules, parser output models |
| API/UI impact | Indexing Status warnings, Workspace Overview, Code Explorer, API Explorer, Graph View |
| Tech stack | Python AST, Tree-sitter, Pydantic parser schemas from `15_parser_output_schema.md` |
| Implementation | Add `ParsedFile`, `ParsedImport`, `ParsedSymbol`, `ParsedEndpoint`, `ParsedApiCall`, `ParsedConfigVariable`, `ParsedDocumentSection`, `ParsedTest`, `ParsedRelation`, `ParserError` |
| Definition of done | Parsers return normalized output instead of directly mutating repository state; indexing persists output consistently |

### 2.2 Python Deep Parser

| Field | Details |
| --- | --- |
| Use cases | U010, U012, U019, U020, U022, U023 |
| Backend/services | Python parser module |
| Frontend | Code Explorer, API Explorer, Impact Analysis, Graph View |
| Tech stack | Python `ast`, optional LibCST/astroid for richer future parsing |
| Extract | imports, classes, functions, methods, decorators, FastAPI routes, calls, SQLAlchemy models, Pydantic schemas, tests |
| Definition of done | FastAPI + SQLAlchemy projects produce endpoints, symbols, models, schemas, calls, tests, and graph relations with line ranges |

### 2.3 JavaScript/TypeScript/React Parser

| Field | Details |
| --- | --- |
| Use cases | U011, U012, U020, U021 |
| Backend/services | JS/TS parser module |
| Frontend | Code Explorer, API Explorer related frontend calls, Graph View |
| Tech stack | Tree-sitter preferred, regex fallback only for incomplete syntax support |
| Extract | imports, exports, functions, arrow functions, React components, fetch/axios calls, test blocks |
| Definition of done | Frontend API calls can be connected to backend endpoints when route strings match |

### 2.4 Docs, Config, Docker, and Tests Parsing

| Field | Details |
| --- | --- |
| Use cases | U010, U014, U023, U024, U025, U030 |
| Backend/services | Markdown parser, config parser, test parser |
| Frontend | Workspace Overview, Search, Settings, Evaluation |
| Tech stack | Markdown parser, PyYAML, tomli, JSON parser, Dockerfile/compose parser |
| Extract | docs sections, config keys, `.env.example` variable names, Docker services, test cases |
| Definition of done | Docs/config/test evidence can appear in search, chat, evaluation, and impact analysis without reading real `.env` files |

### 2.5 Project Mental Model

| Field | Details |
| --- | --- |
| Use cases | U010, U013, U016, U036 |
| Backend/services | `ProjectMentalModelService` |
| API | `GET /repositories/{id}/overview`, `GET /repositories/{id}/reading-path` |
| Frontend | Workspace Overview, AI Assistant suggested questions |
| Tech stack | SQLAlchemy persisted model, deterministic heuristics first, optional LLM summary from evidence later |
| Definition of done | Overview stores detected stack, entrypoints, module map, endpoint summary, docs/test gaps, risk areas, reading path |

## Phase 3 - Hybrid Retrieval and Evidence-First Search

Goal: replace keyword-only search/chat with multi-source retrieval and reliable evidence objects.

### 3.1 Embedding and Vector Store Providers

| Field | Details |
| --- | --- |
| Use cases | U014, U016, U032 |
| Backend/services | `EmbeddingService`, `VectorStoreService`, provider interfaces |
| API/UI impact | Search Page, AI Assistant Chat, Indexing Status embedding step, Settings provider status |
| Tech stack | OpenAI embeddings, sentence-transformers/BGE local option, ChromaDB local, Qdrant/pgvector option |
| Definition of done | Chunks are embedded during indexing, vectors are deleted/rebuilt on re-index, semantic search returns citation-ready evidence |

### 3.2 Hybrid Search

| Field | Details |
| --- | --- |
| Use cases | U014, U015 |
| Backend/services | `SearchService`, `RetrieverService`, evidence ranking |
| API | `GET /repositories/{id}/search?mode=keyword|semantic|hybrid` |
| Frontend | Search Page |
| UI behavior | Search mode selector, scope/entity filters, result type, line range, score, open evidence, ask AI about result |
| Tech stack | BM25 or SQLite FTS/local keyword scoring, vector search, metadata filters, optional reranker |
| Definition of done | Search can find text, files, symbols, endpoints, docs, config, and tests with evidence IDs |

### 3.3 Evidence Lifecycle and Citation Validation

| Field | Details |
| --- | --- |
| Use cases | U015, U016, U018, U034 |
| Backend/services | `EvidenceService`, citation validator |
| API | `GET /evidence/{id}`, `POST /evidence/validate` |
| Frontend | Evidence Viewer, Chat citation chips, Search result detail |
| Tech stack | SQLAlchemy evidence records, index versioning, content hash validation |
| Definition of done | Evidence has source type, file path, line range, snippet/preview, retrieval source, confidence, index version, stale status |

## Phase 4 - API Explorer, Graph View, and Impact Analysis

Goal: make structural code relationships visible and useful for developers and reviewers.

### 4.1 API Explorer and Request Flow

| Field | Details |
| --- | --- |
| Use cases | U019, U020 |
| Backend/services | endpoint detail service, request flow service, graph queries |
| API | `GET /api/endpoints`, `GET /api/endpoints/{endpoint_id}`, `GET /api/endpoints/{endpoint_id}/flow` |
| Frontend | API Explorer |
| UI behavior | Endpoint table, method/path filters, handler detail, frontend API calls, request flow, citations |
| Tech stack | FastAPI metadata extraction, graph traversal, React table/detail panel |
| Definition of done | User can inspect endpoint handler and see evidence-based request flow or clear partial-flow state |

### 4.2 Dependency Graph

| Field | Details |
| --- | --- |
| Use cases | U021 |
| Backend/services | `GraphService`, graph query service |
| API | `GET /graph`, `GET /graph/nodes/{node_id}`, `GET /graph/paths` |
| Frontend | Graph View |
| UI behavior | Graph type selector, relation filters, node filters, focus node, depth, selected node detail, open file, ask AI |
| Tech stack | NetworkX, SQL graph records, React Flow or Cytoscape.js |
| Definition of done | Graph displays meaningful file/symbol/endpoint/API call relations and labels low-confidence relations clearly |

### 4.3 Impact Analysis and Related Tests

| Field | Details |
| --- | --- |
| Use cases | U022, U023 |
| Backend/services | `ImpactAnalysisService`, related tests lookup |
| API | `POST /impact`, `GET /tests/related` |
| Frontend | Impact Analysis page, Code Explorer context actions, Graph View path links |
| UI behavior | Target selector, direct/indirect files, affected endpoints, affected tests, evidence-based vs inferred impact, confidence |
| Tech stack | NetworkX graph traversal, metadata lookup, evidence scoring, React result panels |
| Definition of done | Impact results separate evidence-based impact from inferred impact and include citations where available |

## Phase 5 - Agentic AI Assistant

Goal: implement the differentiating AI workflow: classify, plan, retrieve, verify, answer, and refuse when evidence is weak.

### 5.1 Conversation Persistence

| Field | Details |
| --- | --- |
| Use cases | U016, U017, U018 |
| Backend/services | `ConversationService`, `MessageService`, `ChatService` |
| API | `GET/POST /conversations`, `GET /conversations/{id}`, `DELETE /conversations/{id}`, `POST /chat` |
| Frontend | AI Assistant Chat |
| UI behavior | Chat history, current conversation, answer state, citations, stale citation warnings |
| Tech stack | SQLAlchemy conversation/message tables, TanStack Query, React Router chat routes |
| Definition of done | User can return to previous chats and citations remain inspectable or marked stale after re-index |

### 5.2 Agent Workflow Service

| Field | Details |
| --- | --- |
| Use cases | U032, U033 |
| Backend/services | `AgentWorkflowService`, tool catalog, retriever tools |
| API | `POST /chat`, `GET /messages/{message_id}/agent-trace` |
| Frontend | AI Assistant Chat, Agent Trace panel |
| Tech stack | LangGraph over testable service functions, Pydantic agent state, OpenAI/Azure OpenAI |
| Workflow | classify -> extract entities -> plan -> route tools -> merge evidence -> evaluate -> retry -> answer -> validate |
| Definition of done | Chat response includes question type, citations, evidence sufficiency, missing evidence, and safe agent trace summary |

### 5.3 Evidence Verification and Insufficient Evidence Fallback

| Field | Details |
| --- | --- |
| Use cases | U016, U018, U034 |
| Backend/services | evidence coverage evaluator, citation validator, fallback handler |
| Frontend | AI Assistant Chat, Evidence Viewer |
| UI behavior | Evidence sufficient/insufficient indicator, searched sources, missing evidence list, citation validation state |
| Tech stack | Pydantic structured decisions, deterministic validators, optional LLM verifier constrained by evidence |
| Definition of done | Assistant does not present unsupported claims as facts and refuses or limits answers when evidence is missing |

### 5.4 Multi-Step Investigation and Explanation Modes

| Field | Details |
| --- | --- |
| Use cases | U035, U036 |
| Backend/services | investigation workflow, explanation mode formatter |
| Frontend | AI Assistant Chat, Workspace Overview reading path, Code Explorer context chat |
| UI behavior | Investigation answer with plan, findings, evidence, assumptions, limitations; mode selector: Beginner, Developer, Reviewer |
| Tech stack | LangGraph, OpenAI/Azure OpenAI, structured answer templates, evidence bundles |
| Definition of done | Questions like authentication flow, request flow, impact, and reading path produce multi-step evidence-grounded answers |

## Phase 6 - Settings, GitHub Import, Storage, and Security

Goal: make the product configurable, safe, and ready for realistic demos.

### 6.1 Settings and Provider Configuration

| Field | Details |
| --- | --- |
| Use cases | U024, U026 |
| Backend/services | `SettingsService`, provider test service |
| API | `GET/PATCH /settings`, `GET/PATCH /settings/ignore-patterns`, `GET/PATCH /settings/providers`, `POST /settings/providers/test` |
| Frontend | Settings Page |
| UI behavior | Indexing settings, ignore patterns, provider summaries, provider test, no raw secret display |
| Tech stack | Pydantic Settings, `.env` runtime config, encrypted/secret references later |
| Definition of done | User can see provider readiness and update non-secret settings without exposing keys |

### 6.2 Security Filter and Secret Scanning

| Field | Details |
| --- | --- |
| Use cases | U001, U002, U025 |
| Backend/services | scanner, security filter, import diagnostics |
| Frontend | Import Preview, Indexing Status, Settings |
| UI behavior | Secret-like files skipped, security warnings safe to display, ignore pattern visibility |
| Tech stack | deterministic file rules, optional detect-secrets/trufflehog-style scanner later |
| Definition of done | Real `.env`, private keys, credentials, dependency folders, build outputs, cache, and binaries are never indexed or embedded |

### 6.3 GitHub Import and Sync

| Field | Details |
| --- | --- |
| Use cases | U004, U005 |
| Backend/services | `GitProvider`, import session GitHub source, sync service |
| API | `POST /import-sessions/github`, `POST /repositories/{id}/sync` |
| Frontend | Import Wizard GitHub source, Project Dashboard sync action, Indexing Status |
| UI behavior | URL validation, branch selection, auth-required state, commit metadata, sync latest, stale recommendation |
| Tech stack | GitPython or CLI git wrapper, GitHub API, token references, provider abstraction |
| Definition of done | Public repos import safely; private repos use configured token references and never log raw tokens |

### 6.4 Storage Management

| Field | Details |
| --- | --- |
| Use cases | U027, U028 |
| Backend/services | storage service, cleanup jobs, repository delete |
| API | repository delete, future storage summary endpoint |
| Frontend | Settings storage section, Project Dashboard delete flow |
| Tech stack | local filesystem provider, SQLAlchemy cascade rules, Docker volumes for demo |
| Definition of done | User can delete project data safely; cleanup never escapes managed storage boundaries |

## Phase 7 - Evaluation and Demo Readiness

Goal: prove that adaptive agentic retrieval improves reliability compared with keyword search and naive RAG.

### 7.1 Sample Project and Demo Checklist

| Field | Details |
| --- | --- |
| Use cases | U029, U030 |
| Backend/services | sample fixture importer, demo seed service |
| Frontend | Project Dashboard, Evaluation Page, docs demo checklist |
| UI behavior | Import sample project, suggested demo questions, reset/re-index sample |
| Tech stack | fixture repositories, pytest integration fixtures, Docker Compose demo |
| Definition of done | A new evaluator can run the demo without private data or manual setup |

### 7.2 Evaluation Datasets and Runs

| Field | Details |
| --- | --- |
| Use cases | U030 |
| Backend/services | `EvaluationService`, benchmark runner, metric calculators |
| API | `GET/POST /evaluation/datasets`, `POST /evaluation/runs`, `GET /evaluation/runs/{id}`, `GET /evaluation/runs/{id}/results` |
| Frontend | Evaluation Page |
| UI behavior | Dataset selector, method selector, run status, aggregate metrics, per-question result table, evidence links |
| Tech stack | custom benchmark JSON, SQLAlchemy evaluation tables, optional RAGAS/DeepEval |
| Definition of done | Product can compare keyword search, naive RAG, hybrid retrieval, and adaptive agentic retrieval |

### 7.3 Quality Metrics

| Field | Details |
| --- | --- |
| Use cases | U030, U034 |
| Backend/services | metric calculators |
| Frontend | Evaluation Page |
| Metrics | retrieval precision, retrieval recall, citation accuracy, answer correctness, groundedness, hallucination rate, completeness, insufficient-evidence accuracy, latency, agent trace quality |
| Definition of done | Evaluation run produces repeatable metrics and links weak cases back to evidence/search/chat results |

## Phase 8 - Optional Multi-User or Cloud Extension

Goal: only implement if the product moves beyond local single-user demo.

| Field | Details |
| --- | --- |
| Use cases | U031 |
| Backend/services | user service, auth service, project access control |
| API | auth/session endpoints, project sharing endpoints |
| Frontend | Login page, project sharing settings, role badges |
| Tech stack | JWT/session auth, OAuth optional, PostgreSQL recommended |
| Definition of done | Viewer/Reviewer/Maintainer/Owner permissions are enforced in API and UI |

## Cross-Phase API and UI Coverage

| Frontend surface | Roadmap phases | Required feature behavior |
| --- | --- | --- |
| Project Dashboard | 1, 6, 7 | List, filter, open, re-index, delete, sync GitHub, import sample |
| Import Wizard | 1, 6 | ZIP/folder/GitHub source, config, preview, duplicate handling, security warnings |
| Indexing Status | 1, 2, 3 | Progress, diagnostics, embedding step, graph step, mental model step |
| Workspace Overview | 1, 2, 5 | Mental model, stack, modules, reading path, suggested questions |
| Code Explorer | 1, 2, 3 | File tree, Monaco viewer, symbols, endpoint badges, citation ranges |
| Search Page | 3 | Keyword, semantic, hybrid, filters, evidence-backed results |
| Evidence Viewer | 1, 3, 5 | Evidence detail, stale warning, validate, open source |
| API Explorer | 4 | Endpoint list, endpoint detail, request flow, frontend API calls |
| Graph View | 4 | Graph filters, focus node, path view, relation confidence |
| Impact Analysis | 4, 5 | Target impact, related tests, evidence-based vs inferred results |
| AI Assistant Chat | 3, 5 | Conversations, citations, insufficient evidence, agent trace, explanation modes |
| Evaluation Page | 7 | Dataset, run, metrics, per-question analysis |
| Settings Page | 6 | Providers, ignore patterns, storage, security, test provider connection |

## Implementation Order Recommendation

1. Finish repository/import/indexing reliability and UI diagnostics.
2. Normalize parser output and improve Python/JS/TS/docs/config/test extraction.
3. Add embedding and vector store providers.
4. Build hybrid search and evidence lifecycle.
5. Add endpoint detail, symbol detail, graph queries, and Code Explorer depth.
6. Add API Explorer, Graph View, and Impact Analysis.
7. Persist conversations and implement agent workflow with LangGraph.
8. Add evidence verifier, insufficient-evidence handling, and agent trace UI.
9. Add provider settings, GitHub import/sync, and storage management.
10. Add evaluation datasets, benchmark runner, demo checklist, and CI.

## Portfolio Milestones

### Milestone A - Reliable Local Workspace

Deliverable:

- Import ZIP/folder.
- Preview before indexing.
- Indexing status and diagnostics.
- Workspace overview.
- Code Explorer.
- Search.
- Chat with basic citations.
- Evidence viewer.

Why it matters for CV:

- Shows full-stack product engineering, local-first storage, parsing, API design, and evidence-grounded UX.

### Milestone B - Code Intelligence Product

Deliverable:

- Normalized parser output.
- Python + JS/TS + docs/config/test extraction.
- Project mental model.
- API Explorer.
- Graph View.
- Impact Analysis.

Why it matters for CV:

- Demonstrates AST parsing, Tree-sitter direction, graph modeling, code intelligence, and maintainable architecture.

### Milestone C - Agentic RAG Product

Deliverable:

- Hybrid retrieval.
- Vector search.
- LangGraph workflow.
- Evidence verifier.
- Multi-step investigation.
- Agent trace.

Why it matters for CV:

- Demonstrates modern AI engineering beyond naive RAG: planning, tool use, retrieval orchestration, citation validation, and anti-hallucination design.

### Milestone D - Evaluation and Demo Product

Deliverable:

- Benchmark datasets.
- Evaluation runs.
- Metrics dashboard.
- Docker Compose demo.
- GitHub Actions CI.

Why it matters for CV:

- Shows measurable AI quality, reproducibility, testing discipline, and production-minded delivery.

## Documentation Alignment Checklist

Before marking a feature complete:

- `01_feature_catalog.md`: related use case acceptance criteria are satisfied.
- `02_system_architecture.md`: implementation follows service/provider boundaries.
- `03_data_model.md`: required entities and lifecycle rules are represented.
- `04_api_contract.md`: public response shapes are stable and safe.
- `05_indexing_pipeline.md`: indexing stages, warnings, skipped files, failed files, and re-index behavior are correct.
- `06_agent_workflow.md`: chat/agent features follow classify-plan-retrieve-verify-answer flow.
- `07_evidence_and_citation.md`: evidence and citations are valid, inspectable, and stale-aware.
- `08_frontend_workspace_ux.md`: feature has a visible page, panel, action, or `In development` state.
- `10_evaluation_plan.md`: evaluation features produce repeatable metrics.
- `13_environment_and_config.md`: settings do not expose raw secrets.
- `14_storage_design.md`: storage and deletion stay inside managed boundaries.
- `15_parser_output_schema.md`: parser output is normalized and confidence-labeled.
- `16_error_handling_and_fallback.md`: errors map to user-facing UI states.
- `17_testing_plan.md`: unit, integration, frontend, or evaluation tests exist for the feature.

