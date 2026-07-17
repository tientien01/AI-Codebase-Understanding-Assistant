---
id: RET-004
title: Benchmark Ollama dense embeddings against sparse retrieval
status: completed
priority: P1
phase: 4
owner: project-maintainer
last_verified: 2026-07-17
depends_on: [EVA-001, AGT-007]
requirements: []
contracts:
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
  - docs/10-ai-rag-and-evaluation/specifications/detailed-evaluation-plan.md
  - docs/15-plans/stateful-local-assistant.md
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/services/chat/ollama_client.py
  - backend/app/services/evaluation/**
  - tests/evaluation/**
  - evaluation/results/ret-004-embeddinggemma.json
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-4-retrieval-and-evidence.md
  - docs/15-plans/stateful-local-assistant.md
  - docs/16-agent-tasks/retrieval-agent/RET-004-ollama-dense-embedding-benchmark.md
  - docs/18-production-evidence/ollama-dense-embedding-benchmark-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/api/**
  - backend/app/db/**
  - backend/app/services/indexing/**
  - backend/app/services/retrieval/**
  - backend/migrations/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/**
  - storage/**
dependency_changes: { allowed: false, add: [], remove: [] }
production_gates:
  - The frozen EVA-001 cases and identical per-case candidate inputs are used for sparse, Ollama dense and sparse+dense hybrid methods.
  - The run freezes dataset, fixture, code, model name/digest, vector dimension, preprocessing, method configuration, repetition, cache and capacity identities.
  - Three sequential real-provider repetitions report per-case quality, insufficient-evidence behavior, corpus embedding time, query latency and Ollama model memory.
  - Dense inputs are bounded, sent only to the validated loopback Ollama endpoint and never sourced outside the inert evaluation fixture.
  - RET-005 adoption requires no hybrid regression in macro recall@3, reciprocal rank or insufficient-evidence accuracy, at least 0.01 gain in recall@3 or reciprocal rank, p95 query latency at most 2000 ms, corpus embedding time at most 30000 ms and model memory at most 2 GiB.
  - A failed provider, malformed vector, identity mismatch, non-finite score or unmet adoption rule records a fail-closed rejection and does not alter production retrieval.
evidence_outputs:
  - evaluation/results/ret-004-embeddinggemma.json
  - docs/18-production-evidence/ollama-dense-embedding-benchmark-report.md
---

# RET-004 — Ollama dense embedding benchmark

## Objective

Measure real local `embeddinggemma` dense retrieval against the existing sparse
baseline and a deterministic sparse+dense hybrid on the frozen EVA-001 inputs.

## Scope and method

- Reuse the validated six-case EVA-001 dataset and metrics.
- Embed each unique candidate span once per repetition, then embed every question.
- Rank dense candidates by cosine similarity and fuse sparse+dense ranks with a
  versioned weighted RRF configuration.
- Execute three sequential repetitions with cold/warm timing disclosed, capture the
  Ollama model digest/dimension and `/api/ps` memory snapshot, and persist per-case
  results plus aggregates.
- Produce a deterministic adoption decision for RET-005 without changing current
  retrieval, indexing, configuration defaults or APIs.

## Required commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/evaluation/test_ollama_embeddings.py tests/evaluation/test_ollama_benchmark.py -q
backend\.venv\Scripts\python.exe -m pytest tests/evaluation tests/retrieval -q
backend\.venv\Scripts\python.exe -m app.services.evaluation.ollama_benchmark --dataset evaluation/datasets/retrieval-v1 --fixture-root tests/fixtures/retrieval_benchmark_repo --model embeddinggemma --base-url http://127.0.0.1:11434 --repetitions 3 --output evaluation/results/ret-004-embeddinggemma.json --code-revision RET-004-local --index-version idx_ret_004
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check -- backend/app/services/chat/ollama_client.py backend/app/services/evaluation tests/evaluation evaluation/results/ret-004-embeddinggemma.json docs
```

## Rollback

Remove the benchmark-only adapter, runner, tests and result. Production sparse
retrieval remains unchanged and no index or data migration is required.

## Verification

Completed locally on 2026-07-17. Ten focused fake-provider tests pass, the
evaluation/retrieval gate passes 76 tests, and the final canonical-LF backend gate
passes 384 tests with 31 declared integration-profile skips. Three real local
`embeddinggemma:latest` repetitions satisfy every reviewed adoption rule and record
`adopt_for_ret_005`. Exact identities, per-case results, latency, memory, the metric
deduplication correction and limitations are published in the linked raw result and
production-evidence report.
