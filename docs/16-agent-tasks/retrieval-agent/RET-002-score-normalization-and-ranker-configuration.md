---
id: RET-002
title: Add versioned score normalization and ranker configuration
status: completed
priority: P0
phase: 4
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [RET-001]
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
  - docs/16-agent-tasks/retrieval-agent/RET-002-score-normalization-and-ranker-configuration.md
  - docs/18-production-evidence/ranking-regression-report.md
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
  - Ranking configuration is immutable, canonically serialized, content-addressed, and records enabled retrievers, candidate limits, normalization/fusion methods, weights, support filters, deduplication, diversity, final limit, and context budget.
  - Production baseline fusion uses reciprocal-rank fusion and never directly adds incomparable retriever raw scores.
  - Candidates are filtered by request ownership, index version, retriever policy, per-retriever limit, and support type before fusion.
  - Deduplication uses repository, index, entity, source, and source span while merging retriever, reason, term, and provenance contributions deterministically.
  - Final tie order is fused score, support strength, best individual rank, canonical entity key, then stable candidate ID.
  - Ranking is invariant to candidate input order and raw-score rescaling that preserves per-retriever rank.
  - Blank and unrelated queries still return no ranked results and preserve insufficient-evidence behavior.
evidence_outputs:
  - docs/18-production-evidence/ranking-regression-report.md
---

# Task RET-002 — Add versioned score normalization and ranker configuration

## Context

`RET-001` introduced typed candidates, but `RetrievalService` still selects the maximum projected raw score per chunk. Raw scores from lexical, graph and semantic retrievers are not comparable, and the active ranking policy is neither versioned nor inspectable.

## Objective

Add an immutable content-addressed ranking configuration and deterministic reciprocal-rank fusion that projects typed candidates into the existing hybrid search interface with a reproducible ranking regression.

## In scope

- Strict retriever policies and ranking configuration identity/canonical serialization.
- Rank-only normalization and reciprocal-rank fusion with explicit `rrf_k` and weights.
- Pre-fusion ownership, index, retriever, per-source limit and support filters.
- Repository/index/entity/source/span deduplication with stable contribution merging.
- Deterministic final tie-breaking and bounded result projection.
- Integration into `RetrievalService.hybrid_search` without changing API/search/assistant signatures.
- Hand-computed RRF, input-order/raw-scale invariance, filter/dedup/tie, configuration-validation and insufficient-evidence regressions.

## Out of scope

Learned rerankers, persistent configuration storage, database/API/frontend changes, evidence eligibility/selection, context construction, runtime token truncation, agent workflow changes, evaluation datasets, accepted quality/latency thresholds, provider calls, and release readiness.

## Existing code to reuse

- RET-001 `RetrievalRequest`, `RetrievalCandidate`, controlled enums and typed retriever ranks.
- Existing `RetrievalService` and `HybridSearchMatch` compatibility interfaces.
- Accepted RRF formula and deterministic tie order in the runtime contract.

## Implementation sequence

1. Define immutable retriever-policy, ranking-config and ranked-result contracts with canonical content identity.
2. Validate/filter candidates, enforce per-retriever limits and deduplicate owned source spans.
3. Fuse by weighted RRF, normalize only for compatibility display, and apply deterministic tie-breaking.
4. Integrate the ranker into `RetrievalService` and preserve negative/insufficient behavior.
5. Add the ranking regression matrix, run gates and publish evidence/baseline/status updates.

## Data/API compatibility and migration

No migration or public schema change. Search and assistant callers retain the current method signatures. Result scores become bounded RRF projections rather than projected raw retriever scores; ordering and scores are protected by the RET-002 regression matrix.

## Failure, security, performance, and observability requirements

- Configuration rejects duplicate/missing retriever policies, invalid limits/weights, unsupported methods, invalid support filters, non-positive budgets and non-finite numeric values.
- Ranker rejects cross-repository/index candidates and performs no filesystem, database, network, provider, source execution or source-controlled tool selection.
- All set/list merges and final ordering are stable; candidate count is bounded before and after fusion.
- Configuration identity changes for any ranking-policy field and remains identical under repeated construction.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/retrieval/test_ranking.py -q
backend\.venv\Scripts\python.exe -m pytest tests/retrieval tests/test_service_boundaries.py tests/test_code_analysis.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The local profile is used. PostgreSQL/Redis-only tests may retain declared skips. The ranking regression includes insufficient-evidence cases and records exact configuration identity/formula limitations in `docs/18-production-evidence/ranking-regression-report.md`.

## Acceptance criteria

- Default configuration serializes canonically and has a stable content-derived `rankcfg_` identity.
- Hand-computed weighted RRF and bounded normalized projections match exact expected values.
- Cross-owner/version, disabled retriever, over-limit and disallowed-support candidates are rejected or filtered deterministically as declared.
- Duplicate source spans merge contributions without losing retriever, reason, term or provenance data.
- Candidate reorder and raw-score rescaling do not change ranked identities/order/scores when retriever ranks are unchanged.
- Existing retrieval/classification and insufficient-evidence regressions continue to pass.
- Targeted ranking, retrieval compatibility, full backend and diff-hygiene gates pass.

## Rollback

Restore the RET-001 max-score compatibility projection and remove the unused ranking module/tests/docs. No persisted configuration or migration rollback is required.

## Documentation and evidence updates

After all commands pass, publish the ranking regression report, update source/test/capability baselines and Phase 4 status, mark this task completed, and advance the next candidate to `RET-003`.

## Closing evidence

- Default `ranking-config/v1` is canonically serialized as `rankcfg_277eb94cb50ff8583271fba2` and records every required policy field.
- Owned candidates are filtered and deduplicated before rank-only weighted RRF; merged terms/reasons/provenance and deterministic support/rank/entity/ID ties are retained.
- The 18-test ranking gate, 61-test retrieval/service/code-analysis regression and 186-pass/29-skip local-profile backend suite completed successfully.
- Learned ranking, persistent configuration, evaluation datasets/thresholds and evidence/context selection remain explicitly assigned to later tasks.
