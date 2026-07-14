---
id: EVA-001
title: Implement versioned retrieval datasets, comparison baselines, and a reproducible evaluation runner
status: completed
priority: P0
phase: 4
owner: project maintainer
last_verified: 2026-07-14
depends_on: [RET-003]
requirements:
  - docs/01-product/success-metrics.md
  - docs/01-product/non-functional-requirements.md
contracts:
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
  - docs/10-ai-rag-and-evaluation/specifications/detailed-evaluation-plan.md
  - docs/11-testing/fixture-catalog.md
  - docs/11-testing/specifications/detailed-testing-plan.md
decisions: []
technology_docs:
  - backend/pyproject.toml
  - backend/requirements-lock.txt
allowed_paths:
  - docs/16-agent-tasks/evaluation/EVA-001-versioned-datasets-baselines-runner.md
  - backend/app/services/evaluation/
  - evaluation/datasets/retrieval-v1/
  - tests/evaluation/
  - tests/fixtures/retrieval_benchmark_repo/
  - docs/11-testing/fixture-catalog.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/15-plans/phases/phase-4-retrieval-and-evidence.md
  - docs/18-production-evidence/retrieval-evaluation-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/
  - backend/app/db/
  - backend/app/services/chat/
  - backend/app/services/evidence/
  - backend/app/services/indexing/
  - backend/app/services/retrieval/
  - frontend/
  - storage/
  - imported repositories or runtime datasets
  - secret and credential files
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - versioned evaluation-case/v1 dataset with content-bound identity
  - exact/keyword, naive semantic top-k, and deterministic hybrid comparison on identical cases
  - deterministic metric formulas and zero-denominator behavior
  - reproducible per-case output and run manifest with frozen identities and checksums
  - negative and ambiguous insufficient-evidence coverage
  - retrieval/evidence/assistant compatibility regression
evidence_outputs:
  - docs/18-production-evidence/retrieval-evaluation-report.md
---

# Task EVA-001 — Implement versioned datasets, baselines, and evaluation runner

## Context

`RET-001` through `RET-003` established typed candidates, deterministic fusion, evidence validation, and bounded context selection. Phase 4 still lacks the versioned benchmark and reproducible same-case comparison required to measure those components against simpler baselines. The project owner authorized EVA-001 on 2026-07-14 after AGT-003 was reviewed and merged.

## Objective

Produce one deterministic retrieval evaluation foundation that validates a versioned `evaluation-case/v1` dataset, evaluates exact/keyword, naive semantic top-k, and deterministic hybrid methods on the same declared candidate observations, calculates reviewed retrieval and insufficient-evidence metrics, and exports reproducible per-case results plus a content-bound run manifest.

## In scope

- Add the synthetic, secret-free `retrieval_benchmark_repo` fixture with exact, lexical, semantic, graph-path, negative, and ambiguous cases.
- Add a versioned JSON dataset whose expected entities, evidence spans, paths, alternatives, answer policy, capability preconditions, and budgets follow `evaluation-case/v1`.
- Validate dataset/case schemas, unique identities, fixture revision, content hashes/ranges, controlled categories, and positive/negative ground truth before a run.
- Reuse typed retrieval candidate and ranking contracts without changing them.
- Implement three deterministic comparison methods over identical case inputs: exact/keyword, naive semantic top-k, and production deterministic hybrid.
- Calculate Recall@k, Precision@k, MRR, nDCG, exact-target rank, duplicate rate, source diversity, and insufficient-evidence accuracy with explicit denominator and undefined-value handling.
- Persist sanitized per-case inputs/outputs, method configuration, candidate/evidence identities, metrics, errors, durations supplied by the run boundary, and aggregate macro results.
- Freeze dataset and fixture revisions, code revision input, index/config/provider identities, seed, capacity profile, cache/concurrency condition, timestamps supplied by the caller, budgets, and output checksums in the run manifest.
- Provide a small CLI/module entry point that reads a declared dataset and writes JSON results without network/provider access.

## Out of scope

- Numeric release-threshold acceptance, CI blocking gates, provider-quality judging, model/embedding adoption, or three production-like threshold runs; those require later evidence and EVA-002.
- A persistent vector database, embedding provider, learned reranker, LLM answer grading, evaluation API/UI, load testing, or production database persistence.
- Changes to retrieval, evidence, assistant, indexing, API, database, frontend, or imported-repository execution behavior.
- Claims that a deterministic semantic candidate fixture proves real embedding quality.

## Existing code to reuse

- `backend/app/services/retrieval/contracts.py` for owned normalized candidates and controlled retriever/support values.
- `backend/app/services/retrieval/ranking.py` for the accepted deterministic hybrid ranking configuration and weighted RRF.
- `backend/app/services/evidence/selection.py` contracts where selected evidence identity is reported; EVA-001 must not weaken or modify selection behavior.
- Existing retrieval, ranking, evidence, and assistant tests as compatibility regressions.

## Implementation sequence

1. Define immutable dataset, case, expected-result, method, metric, per-case-result, and run-manifest models with canonical JSON hashing.
2. Add and validate `retrieval-v1` plus `retrieval_benchmark_repo`, including reviewed source hashes/ranges and negative/ambiguous policies.
3. Implement method adapters that filter the same declared normalized candidates for exact/keyword and naive semantic top-k, and invoke the existing ranker for hybrid.
4. Implement metrics with unit tests using hand-computed examples, empty expectations, duplicate candidates, ties, and negative cases.
5. Implement the deterministic runner/export path and prove identical semantic output/checksums for repeated runs with identical frozen inputs.
6. Run targeted, compatibility, and full local-profile suites; record the dataset identity, commands, results, limitations, and representative comparison in production evidence.

## Data/API compatibility and migration

This task adds internal evaluation contracts and immutable JSON files only. It changes no public API or persistence schema. Existing retrieval candidates are consumed read-only. Schema changes require a new evaluation schema version; an issued dataset version is never edited silently.

## Failure, security, performance, and observability requirements

- Reject malformed, duplicate, cross-fixture, unsupported-schema, hash/range-invalid, or non-finite-score input before scoring.
- Never read runtime repositories, `storage/`, credentials, provider payloads, or source outside the declared synthetic fixture root.
- Do not execute or import fixture content. Fixture revision and evidence hashes are computed as inert bytes with deterministic path ordering.
- Fail closed when a method lacks required capability input; report a controlled unavailable/error result rather than substituting another method.
- Deterministic ordering and canonical serialization must make regressions reviewable. Wall-clock timings and timestamps are caller-supplied observations and excluded from semantic reproducibility comparison where declared.
- Keep candidate and case limits explicit so the deterministic smoke run remains bounded; load/capacity qualification is out of scope.

## Required tests and commands

Run from the repository root with the locked Python 3.11 environment. The benchmark uses only synthetic checked-in files and deterministic candidates; no provider, PostgreSQL, Redis, network, or imported repository is used.

```powershell
$env:PYTHONPATH = "backend"
& backend\.venv-clean\Scripts\python.exe -m pytest tests/evaluation -q
& backend\.venv-clean\Scripts\python.exe -m pytest tests/evaluation tests/retrieval tests/evidence tests/assistant -q
& backend\.venv-clean\Scripts\python.exe -m pytest tests -q
& backend\.venv-clean\Scripts\python.exe -m app.services.evaluation.runner --dataset evaluation/datasets/retrieval-v1 --output .tmp/eva-001-run.json --code-revision EVA-001-local --index-version idx_eva_001 --started-at 2026-07-14T00:00:00Z --completed-at 2026-07-14T00:00:00Z
```

The CLI command runs with `PYTHONPATH=backend` if the environment does not already expose the backend package. Generated `.tmp` output is verification-only and is not committed. Record exact pass/skip/warning counts and the exported dataset/result checksums in `docs/18-production-evidence/retrieval-evaluation-report.md`.

## Acceptance criteria

- The checked-in dataset validates as `evaluation-case/v1`, has a stable content-derived revision, and covers every task-owned category and answer policy.
- All three methods receive identical versioned cases and candidate observations; their configurations and unavailable capabilities are explicit in each result.
- Hand-computed tests pass for Recall@k, Precision@k, MRR, nDCG, rank, diversity, duplicate rate, and insufficient-evidence accuracy, including empty/undefined cases.
- Reordering input where contracts declare order irrelevant does not change ranked IDs, metrics, aggregates, or semantic result checksum.
- Two runs with identical frozen inputs produce the same dataset revision, method identities, per-case results, aggregates, and semantic checksum.
- Invalid source hashes/ranges, duplicate IDs, malformed candidates, path escape, and non-finite values fail before an evidence-quality result is emitted.
- Existing retrieval/evidence/assistant regressions and the full local-profile suite pass without weakening prior assertions.
- The evidence report states that deterministic semantic fixtures are not real embedding/provider quality and that numeric release thresholds remain pending.

## Rollback

Remove the evaluation package, `retrieval-v1` dataset, synthetic fixture, tests, and unissued report. No migration or runtime rollback is required because public APIs, production data, and retrieval behavior are unchanged. Issued evidence is superseded rather than rewritten.

## Documentation and evidence updates

After all commands pass, publish `docs/18-production-evidence/retrieval-evaluation-report.md`, update the fixture catalog and source/test/capability baselines, record Phase 4 and project status accurately, mark this task `completed`, and advance `EVA-002` only as a candidate requiring separate authorization.
