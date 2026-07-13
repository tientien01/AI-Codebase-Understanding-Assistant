---
id: RET-001
title: Split typed retrievers and deterministic query classifier
status: completed
priority: P0
phase: 4
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [INT-004]
requirements: []
contracts:
  - docs/05-domain-contracts/retrieval-evidence-assistant.md
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
  - docs/10-ai-rag-and-evaluation/specifications/detailed-evaluation-plan.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/services/retrieval/**
  - tests/retrieval/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-4-retrieval-and-evidence.md
  - docs/16-agent-tasks/retrieval-agent/RET-001-typed-retrievers-and-query-classifier.md
  - docs/18-production-evidence/retrieval-boundary-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/**
  - backend/app/db/**
  - backend/app/schemas/**
  - backend/app/services/chat/**
  - backend/app/services/evidence/**
  - backend/app/services/indexing/**
  - backend/app/services/repositories/**
  - backend/app/workers/**
  - backend/migrations/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Query classification is deterministic, typed, and preserves the existing compatibility labels.
  - Exact, lexical, symbol, endpoint, metadata, graph, and optional semantic retrieval use one immutable request and candidate contract.
  - Candidates retain repository/index ownership, retriever identity/version, rank, matched terms, reason codes, support type, and provenance references.
  - Existing search and assistant callers retain the current RetrievalService interface and observable result ordering for the regression matrix.
  - Empty and unrelated queries return no candidates and preserve the insufficient-evidence path.
  - Retriever failures cannot silently manufacture candidates or cross repository/index ownership.
evidence_outputs:
  - docs/18-production-evidence/retrieval-boundary-report.md
---

# Task RET-001 — Split typed retrievers and deterministic query classifier

## Context

The current `RetrievalService` combines query classification, lexical scoring, entity lookup, graph expansion, semantic retrieval, deduplication, score projection, and answer compatibility in one module. Its behavior is a useful deterministic baseline, but retrievers do not yet share the accepted normalized request/candidate boundary.

## Objective

Introduce a deterministic typed query classifier and typed retriever adapters while preserving the current `RetrievalService` API and the verified local retrieval behavior.

## In scope

- Immutable query classification, retrieval request, and normalized candidate contracts.
- Exact, lexical/chunk, symbol, endpoint, metadata/file, graph/context, and optional local-semantic retriever adapters.
- Stable candidate ownership, IDs, ranks, reason codes, support type, and provenance fields.
- Compatibility projection back to `HybridSearchMatch` and the current question-type strings.
- Deterministic positive, tie/order, empty-query, unrelated-query, and insufficient-evidence regression cases.

## Out of scope

RRF or other fusion changes, score normalization policy, ranking configuration persistence, evidence selection, context budgeting, agent workflow changes, database/API/frontend changes, provider calls, benchmark threshold acceptance, and production release claims.

## Existing code to reuse

- `RetrievalService` scoring and compatibility output.
- `LocalVectorSearchService` deterministic sparse-vector provider.
- Existing repository, chunk, symbol, endpoint, graph, search, assistant, and evidence compatibility models.

## Implementation sequence

1. Add strict query and candidate contracts plus deterministic ownership/ordering validation.
2. Extract query classification behind a typed classifier with compatibility labels.
3. Split current retrieval sources into typed adapters using the existing scoring behavior.
4. Project typed candidates into the current hybrid result interface without changing callers.
5. Add the regression matrix, run gates, and publish evidence/baseline/status updates.

## Data/API compatibility and migration

No migration or public API change. `RetrievalService.classify_question`, `search_chunks`, `hybrid_search`, and `HybridSearchMatch` remain compatible. Normalized candidates are an internal boundary for later `RET-002` fusion work.

## Failure, security, performance, and observability requirements

- Retrieval reads only the supplied in-memory repository/index state and performs no filesystem, database, network, provider, or source execution.
- Requests reject blank ownership, non-positive limits, and invalid versions; candidates reject mismatched ownership, invalid rank, non-finite scores, and uncontrolled enum values.
- Candidate IDs and tie ordering are deterministic; input source text cannot select tools or retriever implementations.
- Optional semantic retrieval may return no candidates without changing deterministic exact/lexical behavior.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/retrieval -q
backend\.venv\Scripts\python.exe -m pytest tests/retrieval tests/test_service_boundaries.py tests/test_code_analysis.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The local profile is used. PostgreSQL/Redis-only tests may retain declared skips. The retrieval regression command must include insufficient-evidence cases, and exact results and limitations are recorded in `docs/18-production-evidence/retrieval-boundary-report.md`.

## Acceptance criteria

- Every enabled retriever accepts the same typed request and emits the same typed candidate schema.
- Query labels and current hybrid result behavior remain compatible for the regression matrix.
- Candidate ownership/version, identity, ranks, reasons, support, and provenance are stable under repeated runs.
- Blank/unrelated queries produce zero candidates and the existing agent insufficient-evidence behavior remains reachable.
- Targeted retrieval, service/code-analysis regression, full backend, and diff-hygiene gates pass.

## Rollback

Restore the monolithic retrieval implementation and remove the unused typed boundary/tests/docs. No persisted data or migration rollback is required.

## Documentation and evidence updates

After all commands pass, publish the retrieval boundary report, update source/test/capability baselines and Phase 4 status, mark this task completed, and advance the next candidate to `RET-002`.

## Closing evidence

- Exact, lexical, symbol, endpoint, metadata, graph/context and optional sparse-semantic adapters now emit one owned immutable candidate contract behind the existing `RetrievalService` API.
- Query classification is typed and deterministic while preserving all existing compatibility labels.
- The 16-test retrieval gate, 43-test retrieval/service/code-analysis regression and 168-pass/29-skip local-profile backend suite completed successfully.
- Ranking configuration/fusion, evaluation datasets and evidence/context selection remain explicitly assigned to later Phase 4 tasks.
