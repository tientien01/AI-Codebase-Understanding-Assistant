# Testing Plan

## Document Purpose

This document defines the testing strategy for AI Codebase Assistant. It focuses on correctness, regression prevention, security behavior, and end-to-end product flows. It is separate from `10_evaluation_plan.md`, which measures retrieval and answer quality against baselines.

## Goals

Tests must protect the behaviors most likely to break:

- security filtering;
- repository ingestion and import preview;
- duplicate detection;
- indexing and re-indexing;
- parser extraction;
- chunk metadata;
- persistence and index versioning;
- graph relations;
- retrieval ranking;
- evidence validation;
- agent workflow;
- API error handling;
- frontend workflows.

## Fixtures

Primary fixture:

```text
tests/fixtures/fastapi_react_sample/
```

It should contain:

- FastAPI app entrypoint.
- Auth router with `/login`.
- Auth service.
- Security/token helper.
- User model or schema.
- React login page.
- Frontend API service.
- README.
- `.env.example`.
- Dockerfile or docker-compose.
- At least one test file.

It must not contain:

- `.env`;
- real secrets;
- node_modules;
- dist;
- build;
- venv.

Additional fixtures:

- repository with parser errors;
- repository with no indexable files;
- repository with secret files that must be skipped;
- repository with docs-only content;
- repository with duplicate source content;
- repository with changed file for re-index/stale citation tests;
- repository with unsupported file types.

## Unit Tests

### File rules

Verify:

- supported extensions are included;
- blocked secret files are skipped;
- dependency/build/cache folders are skipped;
- `.env.example` is allowed;
- absolute paths and `..` paths are rejected.

### Import preview

Verify:

- preview returns detected languages;
- preview returns candidate, skipped, and warning counts;
- secret files are reported as skipped, not read;
- duplicate repository candidates are detected;
- expired import sessions cannot be confirmed.

### Scanner

Verify:

- relative paths are correct;
- file size limit works;
- binary files are skipped;
- warnings are created.

### Python parser

Verify extraction of:

- imports;
- classes;
- functions;
- methods;
- docstrings;
- FastAPI endpoints;
- SQLAlchemy models;
- Pydantic schemas;
- basic calls;
- pytest tests where supported.

### JS/TS parser

Verify extraction of:

- imports;
- functions;
- React components;
- fetch calls;
- axios calls;
- test files where supported.

### Markdown/config parsers

Verify:

- Markdown sections include heading metadata;
- JSON/YAML/TOML parse safely;
- Dockerfile instructions are chunked;
- `.env.example` returns variable names only.

### Chunker

Verify:

- every chunk has citation metadata;
- line ranges are valid;
- content hash is stable;
- symbol chunks link to symbols;
- chunk IDs are stable or traceable enough for vector metadata.

### Store

Verify:

- repository round trip;
- import session round trip if persisted;
- index records round trip;
- re-index clears or supersedes stale records;
- index version increments;
- evidence persists after restart.

### Graph

Verify:

- files define symbols;
- endpoints expose handlers;
- frontend API calls connect to backend endpoints;
- impact traversal returns neighbors;
- graph relations include confidence and evidence where possible.

### Retriever

Verify:

- exact symbol match outranks weak semantic match;
- endpoint lookup finds exact route;
- graph evidence is included for flow questions;
- duplicates are removed;
- insufficient evidence is detected.

### Agent

Verify:

- classifier returns expected question type;
- retrieval plans differ by question type;
- low evidence triggers retry;
- agent trace records tools used;
- answer validation rejects unsupported citations;
- nonexistent target returns insufficient evidence.

### Evidence and citation

Verify:

- evidence IDs can be opened;
- line ranges are valid;
- stale citation is marked after re-index;
- graph evidence points back to file/symbol/endpoint evidence when required.

## Integration Tests

### Indexing pipeline

Steps:

1. Create repository from fixture.
2. Run indexing.
3. Assert repository status is indexed.
4. Assert files, symbols, endpoints, chunks, graph nodes, and edges exist.
5. Assert blocked files are absent.
6. Assert index version is assigned.

### Chat API

Cases:

- login flow returns citations;
- nonexistent endpoint returns insufficient evidence;
- debugging question retrieves config/code evidence when available;
- agent trace is available when enabled.

### Search API

Cases:

- keyword search finds exact symbol;
- semantic search finds related chunk;
- hybrid search returns ranked evidence;
- selected search evidence can be opened in Evidence Viewer.

### Evidence API

Cases:

- citation evidence can be opened;
- wrong repository cannot access evidence;
- missing evidence returns `EVIDENCE_NOT_FOUND`;
- stale evidence returns stale warning metadata.

### Re-index

Cases:

- re-index replaces stale chunks and graph records;
- old vectors are deleted or replaced;
- old chat citations are marked stale when index version changes;
- failed re-index does not present mixed data as completed.

### Settings and providers

Cases:

- settings endpoint does not return raw secrets;
- provider test works with fake provider;
- unconfigured provider returns safe error state.

### Storage cleanup

Cases:

- expired import sessions are deleted;
- delete repository removes managed source and vectors;
- cleanup never deletes paths outside storage roots.

## Frontend Tests

Minimum:

- Project dashboard renders empty and populated states.
- Import wizard validates input and shows preview.
- Duplicate preview choices render correctly.
- Indexing status renders running/failed/completed.
- Workspace overview renders project mental model.
- Chat renders citations and opens evidence viewer.
- Search result opens Code Explorer.
- Stale citation warning renders.
- In-development pages do not render blank pages.

Recommended tools:

- Vitest.
- React Testing Library.
- Playwright for one end-to-end local flow.

## Evaluation Tests

Verify:

- benchmark dataset loads;
- evaluation run creates results;
- metrics are computed;
- export JSON is valid;
- adaptive method result format includes citations and agent trace summary when available.

## End-to-End Smoke Flow

Required local flow:

1. Start backend and frontend.
2. Open Project Dashboard.
3. Import fixture repository.
4. Review preview.
5. Start indexing.
6. Wait for completed status.
7. Open Workspace Overview.
8. Search for `login`.
9. Ask “How does the login flow work?”
10. Open at least one citation.
11. Run impact analysis on an auth symbol.
12. Run evaluation smoke benchmark.
13. Delete repository.

## Required Commands

Backend:

```text
pytest
```

Frontend:

```text
npm run lint
npm run build
```

Optional e2e:

```text
npm run test:e2e
```

## Pass Criteria

The project should not be considered ready if:

- secret files are indexed;
- parser error in one file fails the whole job;
- chat returns technical claims without citations;
- evidence IDs cannot be opened;
- re-index leaves stale mixed data;
- stale citations are not marked;
- provider secrets are returned by API;
- frontend has blank pages for known states.

## Production Test Suites

These suites are required for the P0-P2 production roadmap.

### Canonical Scan Inventory

Cases:

- every indexable file receives canonical file key;
- skipped files have explicit reasons;
- generated/build/dependency folders are skipped;
- secret-like files are skipped;
- later parser output cannot reference file outside scan inventory.

### Parser And Resolver Separation

Cases:

- parser emits raw imports without resolving them;
- resolver maps imports to canonical file/symbol keys;
- unresolved references are retained as diagnostics;
- frontend API calls can resolve to backend endpoints when possible;
- test files can resolve to production targets when possible.

### Canonical IDs

Cases:

- canonical file keys are stable across runs;
- symbol canonical keys survive line-number shifts;
- endpoint canonical keys are stable by method and normalized path;
- duplicate graph candidates merge into one canonical node;
- database IDs can change without breaking canonical comparison.

### Graph Assembly And Validation

Cases:

- duplicate canonical IDs are merged;
- dangling edges are dropped and diagnostics are recorded;
- invalid relation types are normalized or rejected;
- edge provenance is preserved after merge;
- orphan node count is reported;
- graph merge is deterministic.

### Fingerprints And Change Classification

Cases:

- comment-only change does not change structural hash;
- function signature change changes public API hash;
- import change changes dependency hash;
- parser version change triggers reparse for affected language;
- embedding model change triggers re-embedding without full parser rebuild.

### Atomic Activation

Cases:

- failed new index does not change active index version;
- cancellation keeps previous active index;
- vector failure does not mark semantic search ready;
- validation critical failure blocks activation;
- retry does not create duplicate active records.

### Incremental Equivalence

For fixture changes, compare:

```text
clean full rebuild result
vs
incremental rebuild result
```

Expected:

- same canonical graph for unaffected areas;
- same active endpoints;
- same reachable symbols;
- same search answers for unchanged questions;
- changed files and affected dependents are updated.

### Guided Tours

Cases:

- tour steps reference existing files or nodes;
- deleted files are not referenced after re-index;
- tour ordering is deterministic for the same index;
- each step has a reason and learning outcome.

### Capability Readiness

Cases:

- semantic search failure leaves code explorer ready;
- architecture failure leaves graph ready when graph validation passes;
- UI renders limited/failed/in-development states correctly;
- API never reports a capability ready without required artifacts.
