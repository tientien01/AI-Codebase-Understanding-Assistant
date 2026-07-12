# Indexing Pipeline

## Document Purpose

This document expands the indexing architecture described in `02_system_architecture.md`. It defines the detailed indexing pipeline that turns an imported repository into searchable, citable, graph-aware, and agent-ready project knowledge.

This file should answer:

- What happens after a user uploads or imports source code?
- What does the Preview step show before indexing?
- Which files are scanned, skipped, parsed, chunked, embedded, and linked into the graph?
- How are indexing progress, warnings, parser errors, re-indexing, and stale evidence handled?

## Goal

The indexing pipeline turns a repository into searchable, citable, graph-aware knowledge. It must be safe, repeatable, observable, and robust against partial parser failures.

The pipeline should support four outcomes:

1. **Workspace understanding**: project overview, detected stack, important files, modules, endpoints, reading path.
2. **Search and retrieval**: keyword, semantic, symbol, endpoint, config, docs, and test search.
3. **Agentic AI answering**: evidence bundles for grounded LLM answers.
4. **Graph and impact analysis**: file, symbol, endpoint, import, call, API, test, and documentation relations.

## Relationship to Other Docs

- `02_system_architecture.md`: explains where the Indexing Service sits in the full system.
- `03_data_model.md`: defines the tables written by indexing.
- `04_api_contract.md`: defines import session, preview, indexing status, warnings, skipped files, and failed files APIs.
- `06_agent_workflow.md`: consumes indexed metadata, chunks, graph, and evidence for AI answers.
- `07_evidence_and_citation.md`: defines how chunks and parsed metadata become verifiable evidence.

## High-Level Pipeline

```text
repository source
-> validate source
-> create import session
-> scan preview metadata
-> detect duplicates and security warnings
-> user confirms indexing
-> create repository record
-> create indexing job
-> scan files
-> apply security filters
-> detect language and file type
-> read text safely
-> parse files
-> normalize parser output
-> build chunks
-> generate embeddings
-> store vectors
-> build graph
-> generate project mental model
-> generate suggested reading path
-> persist job result
```

## Pipeline Overview Diagram

```mermaid
flowchart TD
    A[Repository Source] --> B[Validate Source]
    B --> C[Create Import Session]
    C --> D[Preview Scan]
    D --> E[Security and Duplicate Check]
    E --> F{User Confirms?}
    F -->|No| X[Cancel Import Session]
    F -->|Yes| G[Create Repository Record]
    G --> H[Create Indexing Job]
    H --> I[Scan and Filter Files]
    I --> J[Detect Language and File Type]
    J --> K[Safe Text Reading]
    K --> L[Parse Files]
    L --> M[Normalize Parser Output]
    M --> N[Create Chunks]
    N --> O[Generate Embeddings]
    O --> P[Store Vectors]
    M --> Q[Build Graph]
    P --> R[Project Mental Model]
    Q --> R
    R --> S[Suggested Reading Path]
    S --> T[Persist Job Result]
```

## Indexing Stage Names

The system should use stable stage names so the frontend and API can show clear progress.

| Stage | Meaning |
| --- | --- |
| `queued` | Job has been created but not started. |
| `validating_source` | Source exists and is safe enough to inspect. |
| `preview_scanning` | Preview metadata, language, size, and warnings are being collected. |
| `waiting_for_confirmation` | Preview is ready and user must confirm indexing. |
| `copying_source` | Source is copied/extracted/cloned into managed storage. |
| `scanning_files` | File candidates are discovered. |
| `filtering_files` | Ignored, unsafe, binary, and unsupported files are skipped. |
| `detecting_language` | Language and file type are inferred. |
| `reading_files` | Text is read safely with encoding detection. |
| `parsing_files` | Parsers extract imports, symbols, endpoints, API calls, models, docs, and config. |
| `normalizing_output` | Parser output is converted into the common schema. |
| `building_chunks` | Citation-ready retrieval chunks are created. |
| `generating_embeddings` | Embedding provider creates vectors. |
| `storing_vectors` | Vector IDs are persisted and linked to chunks. |
| `building_graph` | Graph nodes and edges are created. |
| `building_project_mental_model` | High-level project understanding is generated. |
| `building_reading_path` | Suggested reading path is generated from metadata and graph signals. |
| `completed` | Job completed successfully. |
| `completed_with_warnings` | Job completed but some files were skipped or failed. |
| `failed` | Fatal error prevented useful indexing. |
| `cancelled` | User or system cancelled the job. |

## Step 0: Import Session and Preview

The import session exists before a repository becomes a fully indexed project.

### Purpose

Preview protects the user from indexing the wrong or unsafe source. It also makes the system feel transparent by showing what will be indexed and what will be skipped.

### Supported sources

- Uploaded zip.
- Uploaded folder through browser file picker.
- GitHub public URL.
- GitHub private URL with configured credentials.

### Preview should include

- Project name candidate.
- Source type.
- Estimated repository size.
- Estimated number of files.
- Detected languages and frameworks.
- Top-level folder structure.
- Files/folders to be skipped.
- Security warnings for secret-like files.
- Possible duplicate repositories.
- Estimated index time.
- Whether the project has enough supported files to continue.

### Preview output

The preview should create or return:

- `import_session_id`
- source summary
- detected stack summary
- file statistics
- skipped summary
- security warnings
- duplicate candidates
- recommended action

### Duplicate handling

If a possible duplicate is found, the UI should allow:

- Open existing project.
- Re-index existing project.
- Import as new copy.
- Cancel.

Duplicate signals may include:

- same sanitized source URI
- same GitHub URL
- same branch/commit
- same root folder name plus similar file hash summary
- same archive hash

## Step 1: Source Validation

Validation must happen before indexing and before storing any untrusted source permanently.

### Validation rules

- Source exists.
- Source is not empty.
- Source size is under configured limit.
- Archive paths do not escape target directory.
- Nested archives are rejected or handled with strict depth limits.
- GitHub URL points to an allowed host.
- Credentials are referenced indirectly and never stored in source metadata.
- Real secret files are not read for content.

### Output

- Import session or repository source record.
- Managed source folder at `storage/repositories/{repository_id}/source` after confirmation.
- Validation warnings or fatal validation error.

## Step 2: File Scan

Scanner walks the managed source folder and creates file candidates.

### Ignored folders

- `.git`
- `.svn`
- `.hg`
- `node_modules`
- `venv`
- `.venv`
- `env`
- `dist`
- `build`
- `.next`
- `.nuxt`
- `coverage`
- `.pytest_cache`
- `.mypy_cache`
- `__pycache__`
- `.cache`
- `.idea`
- `.vscode`
- `target`

### Ignored files

- `.env`
- `.env.*` except `.env.example`
- `secrets.*`
- `credentials.*`
- `*.pem`
- `*.key`
- binary files
- unsupported extensions
- files over configured size limit

### Output

Each candidate should include:

- repository_id
- index_version
- relative path
- size
- extension
- detected file type candidate
- initial skip reason if blocked

## Step 3: Language and File Type Detection

### Supported language mapping

| Pattern | Language |
| --- | --- |
| `.py` | `python` |
| `.js`, `.jsx` | `javascript` |
| `.ts`, `.tsx` | `typescript` |
| `.md`, `.mdx` | `markdown` |
| `.json`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.env.example` | `config` |
| `Dockerfile` | `docker` |
| `docker-compose.yml`, `compose.yml` | `compose` |

### File type mapping

- `source`
- `document`
- `config`
- `test`
- `asset`
- `unknown`

### Test detection heuristics

- `tests/`
- `__tests__/`
- `test_*.py`
- `*_test.py`
- `*.test.ts`
- `*.test.tsx`
- `*.spec.ts`
- `*.spec.tsx`

## Step 4: Safe Text Reading

Read order:

1. UTF-8.
2. UTF-8 with BOM.
3. Latin-1 fallback with low confidence.

If all fail:

- mark file `parse_status=failed`
- create parser error or failed-file record
- continue indexing other files

Rules:

- Never read real `.env` files.
- Never log secret-like content.
- Limit preview content length for very large files.
- Preserve line endings only when needed for line range accuracy.

## Step 5: Content Hashing and Index Versioning

### File hash

SHA-256 over raw bytes.

### Chunk hash

SHA-256 over normalized chunk content plus file path and line range.

### Index version

Every successful or attempted indexing job should have an `index_version`.

Records created during indexing should store `index_version`, including:

- FileRecord
- SymbolRecord
- EndpointRecord
- ApiCallRecord
- ChunkRecord
- GraphNode
- GraphEdge
- ProjectMentalModel
- Evidence generated from indexed content

### Purpose

- Re-index correctness.
- Future incremental indexing.
- Evidence reproducibility.
- Stale citation detection.
- Safe cleanup of old index data.

## Step 6: Source Parsers

### Python

Use `ast` as the default parser.

Extract:

- imports
- classes
- functions
- async functions
- methods
- decorators
- docstrings
- FastAPI routes from `app.get`, `app.post`, `router.get`, `router.post`, etc.
- SQLAlchemy models
- Pydantic schemas
- basic function calls
- test functions when file type is `test`

### JavaScript and TypeScript

Preferred parser options:

- tree-sitter
- Babel
- SWC
- TypeScript compiler API

Fallback:

- controlled regex for imports, exports, functions, components, and HTTP calls

Extract:

- imports
- exports
- functions
- arrow functions assigned to constants
- React component heuristics
- fetch/axios calls
- route strings
- test blocks such as `describe`, `it`, `test`

### Markdown

Extract:

- heading hierarchy
- section chunks
- code fences
- links to files or setup commands when visible
- project setup hints
- API documentation hints

### Config

Extract:

- JSON/YAML/TOML keys
- Dockerfile instructions
- docker-compose services
- `.env.example` variable names only

Never read real `.env` files.

## Step 7: Parser Output Normalization

Every parser must return a consistent structure:

```json
{
  "file": {},
  "imports": [],
  "symbols": [],
  "endpoints": [],
  "api_calls": [],
  "models": [],
  "schemas": [],
  "tests": [],
  "relations": [],
  "parser_errors": [],
  "warnings": []
}
```

Rules:

- No parser should write directly to the database.
- The indexing service persists normalized output.
- Unsupported files should produce warnings, not fatal errors.
- Low-confidence extraction must be labeled with confidence.

## Step 8: Chunking

### Chunk types

- `file_summary`
- `function`
- `class`
- `method`
- `component`
- `endpoint`
- `api_call`
- `doc_section`
- `config_section`
- `test_case`

### Required metadata

- repository_id
- index_version
- file_id
- file_path
- language
- file_type
- chunk_type
- symbol_id nullable
- symbol_name nullable
- endpoint_id nullable
- start_line
- end_line
- content_hash

### Rules

- Prefer semantic boundaries over fixed-size chunks.
- Preserve line ranges.
- Keep chunks small enough for retrieval but large enough to understand behavior.
- Add summary chunks only after parser chunks.
- Do not chunk secret or skipped files.

## Step 9: Embedding Generation

Rules:

- Use provider abstraction.
- Batch requests.
- Retry transient failures.
- Do not embed skipped or secret files.
- If embeddings fail fully, mark job failed unless keyword-only mode is explicitly enabled.
- Store embedding provider and embedding model in job metadata.

Output:

- Vector IDs linked to chunk IDs.

## Step 10: Vector Store

Collection name:

```text
repo_{repository_id}
```

Vector metadata must include:

- chunk_id
- repository_id
- index_version
- file_path
- chunk_type
- symbol_name nullable
- start_line
- end_line
- content_hash

Re-index must delete or replace old vectors for the repository and index version according to the retention policy.

## Step 11: Graph Build

### Nodes

- repository
- module
- file
- symbol
- endpoint
- api_call
- model
- schema
- test
- document
- config
- chunk

### Edges

- `contains`
- `defines`
- `imports`
- `exports`
- `calls`
- `exposes_endpoint`
- `calls_api`
- `uses_model`
- `uses_schema`
- `tested_by`
- `documented_by`
- `configured_by`
- `chunks_into`

### Rules

- Store confidence for best-effort relations.
- Preserve evidence line range when available.
- Normalize frontend API call paths and backend endpoint paths to connect them.
- Graph relations must be derived from parser output, metadata, or explicit evidence, not from semantic similarity alone.

## Step 12: Project Mental Model

Generate:

- detected stack
- entrypoints
- module map
- endpoint list
- main flows
- important files
- suggested reading path candidates
- documentation gaps
- test gaps
- config/deployment notes
- risk areas

This model powers:

- Workspace Overview
- Suggested Reading Path
- architecture questions
- onboarding questions
- evaluation baselines

## Step 13: Suggested Reading Path

The suggested reading path recommends 3 to 7 files/modules that a new developer should read first.

### Input signals

- README/docs existence
- application entrypoints
- API routers
- config/database files
- models/schemas
- services/core logic
- high in-degree files in import graph
- high call-degree symbols
- test coverage signals

### Scoring examples

| Signal | Example | Effect |
| --- | --- | --- |
| README exists | `README.md` | strong onboarding candidate |
| Entry point | `main.py`, `app.py`, `server.ts` | high priority |
| Framework initialization | `FastAPI()`, `app.listen()` | high priority |
| Many endpoints | router file | high priority |
| Model/schema definitions | `models.py`, `schemas.py` | medium-high priority |
| Imported by many files | `database.py`, `config.py` | medium priority |
| Service layer | `services/auth_service.py` | medium priority |

### Output item

Each recommendation should include:

- rank
- file_id
- file_path
- title
- reason
- confidence
- signals
- evidence IDs when available

The system must not claim a file is definitely important without explaining the signal.

## Parser Warnings, Skipped Files, and Failed Files

The indexing job should expose detailed diagnostics separately from the main progress response.

### Skipped files

Examples:

- dependency folder
- build output
- binary file
- secret-like file
- unsupported extension
- file too large

### Parser warnings

Examples:

- low-confidence JS/TS regex extraction
- route detected without handler symbol
- graph relation inferred only partially
- markdown link points to missing file

### Failed files

Examples:

- encoding failure
- syntax parse failure
- unexpected parser exception

Rules:

- Skipped files are not failures.
- Parser failure for one file should not fail the whole job unless too many files fail or no useful files remain.
- Warnings must be safe to show to users and must not include secrets.

## Re-index Strategy

### Default complete behavior

1. Create a new indexing job.
2. Increment repository `index_version` or reserve the next index version.
3. Mark repository `indexing`.
4. Preserve conversations and old evidence records.
5. Delete or mark stale old chunks, symbols, endpoints, API calls, graph records, and vectors according to retention policy.
6. Rebuild index from current managed source.
7. Mark repository `indexed` or `indexed_with_warnings` on success.
8. Mark job and repository `failed` on fatal failure.

### Future incremental behavior

- Compare file content hashes.
- Re-parse changed files.
- Remove deleted file records.
- Update dependent graph edges and chunks.
- Recompute affected mental model sections.

## Stale Index Detection

A repository may become stale when:

- managed source files change after `last_indexed_at`
- Git commit changes after GitHub sync
- file hash summary differs from the latest index
- index job failed after partial cleanup

The UI should show a re-index recommendation rather than silently answering from stale data.

## Fatal vs Recoverable Failures

### Recoverable

- one file parse error
- unsupported file type
- encoding failure for one file
- low-confidence JS/TS relation
- missing optional docs
- missing tests

### Fatal

- source folder unavailable
- database unavailable
- vector store unavailable
- embedding provider unavailable after retries
- repository contains no indexable files
- storage path traversal detected
- archive extraction is unsafe

## Observability and API Outputs

The indexing service should support API responses for:

- current job status
- job history
- warnings
- skipped files
- failed files
- stale index status

The main status endpoint should stay compact. Large diagnostics should be paginated or fetched from dedicated endpoints.

## Notes for AI Coding Agents

- Keep scanning, parsing, chunking, embedding, graph build, and mental model generation as separate services or functions.
- Do not let parsers write directly to the database.
- Do not embed or display blocked secret files.
- Make indexing idempotent: repeated indexing should not create duplicate records.
- Preserve line ranges carefully because citations depend on them.
- Treat graph relations as evidence only when they can point back to parser output, file metadata, or line ranges.

## Production Indexing Blueprint

This section is the production direction for future implementation. It refines the earlier pipeline into explicit contracts and activation gates. New code should follow this model even when only part of the pipeline is implemented.

### Priority Levels

P0 is required before the product can be considered production-oriented:

- canonical repository scan inventory;
- parser and resolver separation;
- canonical graph keys;
- graph provenance;
- repository-level validation;
- index version lifecycle;
- atomic index activation;
- fingerprints and change classification;
- incremental affected-set policy.

P1 creates the stronger code-understanding product:

- semantic batch planning;
- architecture layer inference;
- guided tours;
- language and framework adapter registries;
- index quality dashboard;
- graph path evidence.

P2 is advanced:

- deep LLM graph reviewer;
- domain and business-flow view;
- persona-specific tours;
- subdomain graph merging;
- architecture change comparison;
- automatic post-commit updates.

### Production Phase Model

Backend phase model:

```text
Phase 0  - Index Preflight
Phase 1  - Canonical Repository Scan
Phase 2  - Deterministic Structural Parsing
Phase 3  - Symbol and Dependency Resolution
Phase 4  - Graph Candidate Extraction
Phase 5  - Graph Assembly and Normalization
Phase 6  - Repository-Level Validation
Phase 7  - Chunk and Search Index Build
Phase 8  - Architecture and Guided Tour Generation
Phase 9  - Fingerprints and Change Classification
Phase 10 - Atomic Publish
```

The UI does not need to expose all phases. The UI can group them into user-facing stages such as prepare, scan, analyze, build graph, create search index, validate, and publish.

### Phase 0 - Index Preflight

Purpose:

- reserve a new index version;
- lock the repository against concurrent indexing;
- load previous index manifest and fingerprints;
- decide full, partial, architecture-only, search-only, or no-op mode;
- record pipeline component versions.

Input:

```json
{
  "repository_id": "repo_123",
  "requested_profile": "balanced",
  "previous_index_version": 3,
  "force_full": false,
  "source_revision": "commit-or-snapshot-hash"
}
```

Output artifact:

```text
preflight.json
```

Required fields:

- mode;
- base_index_version;
- new_index_version;
- source_revision;
- rebuild_reasons;
- pipeline_versions;
- feature_flags;
- started_at.

Fatal gate:

- if repository lock cannot be acquired, fail with `INDEX_LOCKED`;
- if source cannot be accessed, fail with `REPOSITORY_SOURCE_MISSING`;
- if the new index version cannot be reserved, fail with `INDEX_VERSION_CONFLICT`.

### Phase 1 - Canonical Repository Scan

The scan inventory is the single source of truth for every later phase. A later phase must not process files absent from the scan inventory.

Output artifact:

```text
scan-result.json
```

Each file item should include:

```json
{
  "file_id": "file_backend_app_auth_router_py",
  "canonical_key": "file:backend/app/auth/router.py",
  "relative_path": "backend/app/auth/router.py",
  "language": "python",
  "file_category": "code",
  "size_bytes": 4821,
  "line_count": 131,
  "content_hash": "sha256:...",
  "normalized_content_hash": "sha256:...",
  "is_indexable": true,
  "skip_reason": null,
  "encoding": "utf-8",
  "detected_role": "source",
  "parser_adapter": "python",
  "framework_signals": ["fastapi"],
  "is_generated": false,
  "is_test": false
}
```

File categories:

- code;
- test;
- config;
- docs;
- infra;
- data;
- script;
- markup;
- generated;
- unknown.

Validation checks:

- every indexable file has content hash and canonical key;
- ignored, secret-like, dependency, build, and binary files have explicit skip reasons;
- no file path escapes the repository source root;
- no later artifact references a file outside this inventory.

### Phase 2 - Deterministic Structural Parsing

Parser responsibility:

- read only files from `scan-result.json`;
- extract raw structural facts;
- emit parser output;
- never write database rows directly;
- never resolve cross-file references by guessing.

Parser output must include provenance:

- parser name;
- parser version;
- extraction method;
- confidence;
- source file canonical key;
- line range;
- raw text or normalized snippet when safe.

Output artifacts:

```text
parser-results/{file_id}.json
```

Recoverable failures:

- one file parse error;
- unsupported syntax;
- encoding failure for one file.

Fatal failures:

- no useful parser output remains;
- parser output schema is invalid for mandatory files.

### Phase 3 - Symbol and Dependency Resolution

Parsing and resolution are separate. Parser output contains raw imports, symbols, endpoints, calls, and references. Resolver output maps those raw facts to canonical files, symbols, endpoints, tests, configs, and graph relations.

Resolvers:

- import resolver;
- export resolver;
- qualified symbol resolver;
- inheritance resolver;
- endpoint-handler resolver;
- frontend API call to backend endpoint resolver;
- test to production symbol resolver;
- config usage resolver;
- model/schema usage resolver.

Output artifact:

```text
resolution-result.json
```

Example resolved reference:

```json
{
  "source_file_key": "file:backend/app/api/auth.py",
  "raw_module": "app.services.auth_service",
  "imported_name": "AuthService",
  "resolved_file_key": "file:backend/app/services/auth_service.py",
  "resolved_symbol_key": "class:backend/app/services/auth_service.py:AuthService",
  "resolution_method": "python_absolute_import",
  "confidence": 1.0,
  "provenance": ["parser-results/file_backend_app_api_auth_py.json#import_3"]
}
```

Rule:

- graph edges should be built from resolved relationships whenever possible, not from raw parser text alone.

### Phase 4 - Graph Candidate Extraction

Candidate graph records can come from:

- parser output;
- resolver output;
- framework rules;
- docs/config analysis;
- semantic enrichment;
- architecture inference.

Output artifact:

```text
graph-candidates.json
```

Each candidate must include:

- candidate_id;
- canonical source key;
- canonical target key for edges;
- node or edge type;
- origin;
- confidence;
- evidence references;
- created_by_component;
- component_version.

Allowed origins:

- parser_exact;
- resolver_exact;
- framework_rule;
- heuristic;
- llm_inferred;
- user_confirmed.

### Phase 5 - Graph Assembly and Normalization

Separate graph work into four substeps:

```text
Graph Extraction
-> Graph Assembly
-> Graph Normalization
-> Graph Validation
```

Assembly rules:

- merge duplicate canonical nodes;
- merge duplicate edges by source, target, relation type, and origin;
- preserve all provenance;
- clamp confidence to `0..1`;
- normalize relation direction;
- preserve raw type in metadata when mapping to a canonical type;
- drop dangling edges only after recording validation diagnostics.

Output artifacts:

```text
assembled-graph.json
graph-normalization-report.json
```

### Phase 6 - Repository-Level Validation

Validation is deterministic by default. Optional LLM review can be added later, but it must not replace deterministic validation.

Output artifact:

```text
validation-report.json
```

Coverage checks:

```json
{
  "scan_files": 240,
  "indexable_files": 238,
  "parsed_files": 236,
  "files_with_chunks": 236,
  "file_nodes": 236,
  "unresolved_imports": 11,
  "orphan_nodes": 8,
  "dangling_edges_removed": 3
}
```

Rules:

- every indexable file should be parsed or have a file-scoped diagnostic;
- every parsed file should have a file graph node;
- every symbol used as evidence should have a chunk or line range;
- every endpoint should connect to a handler when framework support exists;
- every graph node file path should exist in scan inventory;
- every guided tour step should point to existing nodes or files.

### Phase 7 - Chunk and Search Index Build

Chunking and retrieval indexes are derived from validated file, symbol, endpoint, graph, and semantic records.

Required outputs:

- chunks;
- chunk manifest;
- keyword index or lexical index state;
- vector index state when enabled;
- retrieval source map.

Output artifact:

```text
chunks-manifest.json
```

If embedding or vector store fails:

- do not fail the whole repository if code explorer, graph, and keyword search can be ready;
- mark `semantic_search` and `chat` capabilities as limited or failed;
- do not activate a vector index that is incomplete without an explicit degraded status.

### Phase 8 - Architecture and Guided Tour Generation

This phase is P1. It can be disabled while P0 remains production-usable.

Inputs:

- validated graph;
- modules;
- endpoints;
- docs;
- framework signals;
- semantic summaries when available.

Outputs:

```text
architecture.json
tours.json
```

Guided tours should support:

- project overview;
- backend request flow;
- authentication or major feature flow;
- database layer;
- deployment or infrastructure;
- testing strategy.

Every tour step must include:

- title;
- target file/node keys;
- explanation;
- why this step comes next;
- learning outcome;
- evidence references or signals.

### Phase 9 - Fingerprints and Change Classification

Output artifact:

```text
fingerprints.json
```

File fingerprint fields:

```json
{
  "file_key": "file:app/auth/service.py",
  "content_hash": "sha256:...",
  "normalized_content_hash": "sha256:...",
  "structure_hash": "sha256:...",
  "public_api_hash": "sha256:...",
  "dependency_hash": "sha256:...",
  "chunk_hash": "sha256:...",
  "parser_version": "python-3.1",
  "framework_rule_version": "fastapi-2.0"
}
```

Change classes:

- unchanged;
- content_only;
- documentation_only;
- structural;
- public_api;
- dependency;
- deleted;
- added;
- parser_version_changed;
- embedding_version_changed;
- enrichment_prompt_changed.

Change policy:

| Change | Required action |
| --- | --- |
| Formatting or comment only | update snippet/chunk only when needed |
| Function body changed | reparse file, chunks, local graph |
| Import/export changed | reparse file plus direct importers/dependencies |
| Public signature changed | reparse reverse dependents |
| Parser version changed | reparse files for that language |
| Embedding model changed | re-embed chunks only |
| Enrichment prompt changed | re-enrich semantic metadata |

Incremental affected set:

```text
changed files
+ direct importers
+ resolved dependencies
+ inheritance neighbors
+ endpoint chains
+ frontend/backend API pairs
+ related tests
```

Implementation should compute:

```text
reanalysis_set = changed_files
relink_set = graph_neighbors(changed_files, allowed_relations)
reenrich_set = affected_semantic_batches(changed_files)
global_recompute = architecture + reading_path + importance_scores
```

### Phase 10 - Atomic Publish

The product should use blue-green index activation:

```text
IndexVersion BUILDING
-> mandatory artifacts persisted
-> graph validated
-> search indexes committed
-> fingerprints saved
-> IndexVersion READY or READY_WITH_WARNINGS
-> Repository.active_index_version = new version
```

If the new index fails:

- mark the new version failed;
- keep the old active version serving search/chat/workspace;
- expose failure diagnostics;
- never present mixed old and new records as a complete index.

Activation requires:

- index manifest exists;
- validation report exists;
- scan inventory exists;
- graph has no critical validation failures;
- mandatory capabilities are ready or explicitly degraded;
- database transaction updates active index version after artifacts and derived records are ready.
