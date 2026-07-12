# Coding Standards

Status: Accepted engineering standard  
Authority: Implementation structure and maintainability rules  
Owner: Engineering owner  
Dependencies: `../README.md`, accepted architecture, domain contracts, ADRs, and technology adoption policy  
Related source: `../../14-implementation-baseline/source-map.md`  
Related tests: lint, typecheck, boundary, unit, integration, contract, and documentation validation  
Last verified: 2026-07-12

## Document Purpose

This document defines engineering rules for implementing AI Codebase Assistant. It is intended for human developers and AI coding agents. The goal is to keep the project maintainable, testable, secure, and aligned with the architecture documents.

## General Principles

- Keep code clear, typed, and maintainable.
- Prefer small services with one responsibility.
- Keep API routes thin.
- Never read or log secrets.
- Add tests for core behavior.
- Do not introduce broad refactors while implementing a narrow feature.
- Keep domain logic testable without UI, FastAPI, LangGraph, or paid providers.
- Prefer explicit models and schemas over unstructured dictionaries when data crosses module boundaries.

## Backend Structure

Recommended:

```text
backend/app/
  api/
    routes/
  core/
    config.py
    errors.py
    logging.py
  db/
    models.py
    session.py
  schemas/
  services/
    repositories/
    ingestion/
    indexing/
    scanning/
    parsing/
    chunking/
    retrieval/
    graph/
    chat/
    evidence/
    evaluation/
    settings/
  providers/
    llm/
    embeddings/
    vector_store/
    git/
  tests/
```

## Python

- Use Python 3.11+.
- Use type hints for public functions.
- Use Pydantic for API schemas.
- Use dataclasses, TypedDict, or Pydantic models for internal structured data.
- Avoid large service classes.
- Avoid passing raw dictionaries across many layers when a model would be clearer.
- Keep parser output aligned with `05-domain-contracts/parsing/detailed-parser-output-schema.md`.

## FastAPI

Routes must:

- validate request;
- call service methods;
- return response schemas;
- map domain errors to the standard API error format.

Routes must not:

- parse files;
- call LLMs directly;
- query vector store directly;
- contain indexing logic;
- perform graph traversal directly;
- build prompts directly.

## Services

Services must be testable without FastAPI.

Recommended constructor dependencies:

- settings;
- repository store;
- provider abstractions;
- logger;
- clock/time provider when timing matters;
- fake provider support for tests.

Avoid hidden global state for domain behavior.

## Agent Workflow

- Use the accepted deterministic state machine by default. Any future workflow framework may orchestrate only after a measured trigger and accepted ADR; domain steps remain plain typed testable functions/classes.
- Define typed agent state.
- Keep tool catalog explicit.
- Log agent trace safely.
- Do not let the LLM invent unsupported tool outputs.
- Agent decisions must be bounded by max retrieval rounds and max evidence count.
- Citation validation must run after answer generation.

## Database

- Use ORM models only for persistence.
- Use schemas/DTOs for API responses.
- Avoid leaking ORM objects to routes.
- Use transactions for multi-table writes.
- Re-index operations must avoid stale mixed states.
- Repository-scoped records must include `repository_id`.
- Versioned index records should include `index_version` where relevant.

## Provider Abstractions

LLM provider interface:

```text
generate_answer(prompt, evidence, options)
```

Embedding provider interface:

```text
embed_texts(texts)
```

Vector store interface:

```text
upsert_chunks(repository_id, chunks, vectors)
search(repository_id, query_vector, filters, limit)
delete_repository(repository_id)
delete_index_version(repository_id, index_version)
```

Git provider interface:

```text
clone_or_download(url, branch, token_ref, target_dir)
sync(repository_source, target_dir)
```

Tests must use fake providers.

## Frontend

- Use React + TypeScript.
- Keep API calls in `src/api`.
- Keep shared types in `src/types`.
- Keep page components separate from API hooks.
- Keep page state local unless shared across pages.
- Use stable loading/error/empty/in-development states.
- Do not hard-code backend URLs outside the API client config.
- Do not display raw internal IDs unless they are useful for debugging views.
- Do not display raw API keys, tokens, or secret values.
- Citation chips must be clickable and open evidence.
- Code paths, symbols, API routes, and line ranges should use monospace styling.

## Error Handling

- Use domain errors with stable codes.
- Return standard API error format.
- Parser errors should usually be recoverable.
- Provider errors should be mapped to user-visible but safe messages.
- Insufficient evidence is not a crash; it is a valid assistant response state.
- Stale citation is a warning state, not necessarily an API failure.

## Logging

Log:

- repository_id;
- job_id;
- conversation_id;
- message_id when useful;
- step;
- error_code;
- safe message;
- tool names used by agent when safe.

Never log:

- API keys;
- raw tokens;
- real `.env` content;
- private credential content;
- full prompts containing sensitive source unless explicitly allowed for local debugging.

## Naming

- Python modules/functions: `snake_case`.
- Python classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- TypeScript components: `PascalCase`.
- TypeScript functions/variables: `camelCase`.
- Database tables: plural `snake_case`.
- API paths: lowercase kebab-case.
- Stable record IDs should use prefixes such as `repo_`, `file_`, `sym_`, `chunk_`, `ev_`, `job_`, `msg_`.

## Comments and Docstrings

- Add comments only for non-obvious decisions.
- Public parser/retriever/agent functions should have short docstrings when behavior is complex.
- Do not write comments that repeat the code.

## Testing Discipline

Add tests for:

- file filtering and security rules;
- import preview and duplicate detection;
- parser extraction;
- chunk metadata;
- persistence and index versioning;
- graph edges;
- retrieval ranking;
- evidence validation;
- agent trace and retry behavior;
- API error handling;
- frontend critical interactions where practical.

Run:

- backend tests after backend changes;
- frontend lint/build after frontend changes;
- evaluation smoke run after retrieval/agent changes when practical.

## Production Indexing Coding Rules

- Every indexing phase must have typed input and output models.
- A phase may read only artifacts declared in its dependency contract.
- Parser code must not write database records directly.
- Resolver code must not use LLMs for relations that static analysis can resolve.
- Canonical keys must be generated by one shared utility.
- Canonical keys must not depend only on line numbers.
- Graph candidates must preserve provenance before normalization.
- Graph normalization must record dropped or changed edges as diagnostics.
- LLM output must pass schema validation and normalizer before storage.
- Inferred output must be labeled as inferred in data and UI.
- Index activation must be atomic.
- Artifact schema must be versioned.
- Capability readiness must be computed from actual artifacts and validation results.
- Do not mark a capability ready if its required artifacts or records are missing.
- Incremental rebuild code must be testable against full rebuild equivalence.

## Service Boundary Rules

Recommended boundaries:

- scanner creates scan inventory;
- parser extracts raw file-local facts;
- resolver maps references to canonical entities;
- graph candidate extractor emits candidate nodes and edges;
- graph assembler merges candidates;
- graph normalizer enforces schema;
- index validator computes quality and readiness;
- index publisher activates the version.

Avoid service classes that scan, parse, resolve, graph, validate, and publish in one method.
