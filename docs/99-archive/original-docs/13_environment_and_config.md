# Environment and Config

## Document Purpose

This document defines runtime configuration, environment variables, safe settings behavior, and test configuration for AI Codebase Assistant. It complements `12_coding_standards.md` and `14_storage_design.md`.

## Principles

- Do not read real `.env` files during repository scanning.
- Runtime configuration may come from process environment variables.
- Only the backend config module should read environment variables directly.
- Raw secrets must not be returned by APIs or rendered in UI.
- Tests should inject settings or use safe defaults.
- Provider settings must support fake providers for automated tests.
- Values shown here are examples for `.env.example`, not real secrets.

## Example Environment Variables

```env
APP_ENV=development
APP_NAME=ai-codebase-assistant
API_V1_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

DATABASE_URL=sqlite:///./storage/app.db

REPOSITORY_STORAGE_DIR=./storage/repositories
UPLOAD_STORAGE_DIR=./storage/uploads
CHROMA_PERSIST_DIR=./storage/chroma
GRAPH_STORAGE_DIR=./storage/graphs
LOG_DIR=./storage/logs
EVALUATION_STORAGE_DIR=./storage/evaluation

ALLOW_LOCAL_PATH_IMPORT=true
LOCAL_PATH_ALLOWLIST=D:/projects;D:/Study
MAX_UPLOAD_SIZE_MB=200
MAX_REPOSITORY_SIZE_MB=500
MAX_FILE_SIZE_MB=1
IMPORT_SESSION_TTL_MINUTES=60
UPLOAD_RETENTION_ENABLED=false

INDEXING_DEFAULT_PROFILE=balanced
INDEXING_BATCH_SIZE=64
INDEXING_MAX_WORKERS=4
INDEXING_ENABLE_PREVIEW=true
INDEXING_ENABLE_INCREMENTAL=false

LLM_PROVIDER=fake
LLM_MODEL=fake-chat-model
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=60

EMBEDDING_PROVIDER=fake
EMBEDDING_MODEL=fake-embedding-model
EMBEDDING_API_KEY=
EMBEDDING_BATCH_SIZE=64

VECTOR_STORE_PROVIDER=chroma
VECTOR_STORE_COLLECTION_PREFIX=repo_

RETRIEVAL_TOP_K=8
EVIDENCE_MIN_SCORE=0.65
MAX_RETRIEVAL_ROUNDS=2
MAX_EVIDENCE_ITEMS=12
ENABLE_AGENT_TRACE=true

GITHUB_TOKEN=
GITHUB_ALLOWED_HOSTS=github.com

ENABLE_EVALUATION=true
EVALUATION_DEFAULT_METHOD=adaptive_agentic
```

## Config Groups

### App

- `APP_ENV`
- `APP_NAME`
- `API_V1_PREFIX`
- `CORS_ORIGINS`

### Storage

- `DATABASE_URL`
- `REPOSITORY_STORAGE_DIR`
- `UPLOAD_STORAGE_DIR`
- `CHROMA_PERSIST_DIR`
- `GRAPH_STORAGE_DIR`
- `LOG_DIR`
- `EVALUATION_STORAGE_DIR`

### Security and Import

- `ALLOW_LOCAL_PATH_IMPORT`
- `LOCAL_PATH_ALLOWLIST`
- `MAX_UPLOAD_SIZE_MB`
- `MAX_REPOSITORY_SIZE_MB`
- `MAX_FILE_SIZE_MB`
- `IMPORT_SESSION_TTL_MINUTES`
- `UPLOAD_RETENTION_ENABLED`

### Indexing

- `INDEXING_DEFAULT_PROFILE`
- `INDEXING_BATCH_SIZE`
- `INDEXING_MAX_WORKERS`
- `INDEXING_ENABLE_PREVIEW`
- `INDEXING_ENABLE_INCREMENTAL`

### LLM

- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`
- `LLM_TIMEOUT_SECONDS`

### Embedding

- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_BATCH_SIZE`

### Vector Store

- `VECTOR_STORE_PROVIDER`
- `VECTOR_STORE_COLLECTION_PREFIX`

### Retrieval and Agent

- `RETRIEVAL_TOP_K`
- `EVIDENCE_MIN_SCORE`
- `MAX_RETRIEVAL_ROUNDS`
- `MAX_EVIDENCE_ITEMS`
- `ENABLE_AGENT_TRACE`

### GitHub

- `GITHUB_TOKEN`
- `GITHUB_ALLOWED_HOSTS`

### Evaluation

- `ENABLE_EVALUATION`
- `EVALUATION_DEFAULT_METHOD`

## Settings API

The settings API may return:

- provider names;
- model names;
- thresholds;
- indexing profile values;
- feature flags;
- storage directories if safe;
- whether a secret is configured as a boolean flag.

The settings API must not return:

- raw API keys;
- GitHub tokens;
- secret file content;
- raw `.env` content;
- private credential content.

## Provider Test Configuration

Provider test endpoints should verify whether the configured provider can be used without exposing secrets.

Expected behavior:

- Return `configured: true/false`.
- Return safe status messages.
- Never echo API keys or tokens.
- Use fake providers in tests.

## Test Configuration

Tests should use:

- temporary SQLite database when practical;
- temporary storage directories;
- fake embedding provider;
- fake LLM provider;
- fake vector store or local disposable vector collection;
- small fixture repositories.

Do not require paid provider keys for automated tests.

## Notes for AI Coding Agents

- Read environment variables only through the backend config module.
- Do not hard-code provider keys or model names in services.
- Use safe defaults in local development.
- Treat `.env.example` as a config documentation file, not as a source of secrets.

## Production Indexing Configuration

Recommended additional config keys:

```env
INDEXING_ENABLE_INCREMENTAL=true
INDEXING_ENABLE_ATOMIC_PUBLISH=true
INDEXING_ENABLE_ARTIFACTS=true
INDEXING_ARTIFACT_RETENTION_DAYS=7
INDEXING_DEBUG_ARTIFACT_RETENTION_DAYS=3

INDEXING_MAX_PARALLEL_PARSE_WORKERS=4
INDEXING_MAX_PARALLEL_SEMANTIC_BATCHES=2
INDEXING_MAX_DEPENDENCY_DEPTH=1
INDEXING_REBUILD_THRESHOLD_PERCENT=30

INDEXING_ENABLE_SEMANTIC_ENRICHMENT=true
INDEXING_ENABLE_ARCHITECTURE_INFERENCE=true
INDEXING_ENABLE_GUIDED_TOURS=true
INDEXING_ENABLE_DEEP_REVIEW=false

GRAPH_SCHEMA_VERSION=2
PARSER_BUNDLE_VERSION=3
CHUNKER_VERSION=2
RESOLVER_RULE_VERSION=1
FRAMEWORK_RULE_VERSION=1
ENRICHMENT_PROMPT_VERSION=4

CAPABILITY_REQUIRE_GRAPH_FOR_CHAT=false
CAPABILITY_REQUIRE_SEMANTIC_SEARCH_FOR_CHAT=false
```

Rules:

- version config values must be included in index manifests;
- changing parser, resolver, graph, chunker, embedding, or prompt versions can trigger partial rebuild;
- local development can disable semantic enrichment and guided tours without disabling deterministic indexing;
- provider keys must never be returned by settings APIs.

## Capability Defaults

Local default should prefer deterministic readiness:

```text
code_explorer: ready when scan + file records are valid
keyword_search: ready when chunks or lexical index exist
graph: ready when graph validates without critical errors
semantic_search: ready only when vector index is committed
chat: ready or limited based on retrieval/evidence availability
architecture: ready only when architecture artifact exists
guided_tours: ready only when tour artifact exists
```
