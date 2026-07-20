---
id: RET-005
title: Add a versioned dense embedding index after benchmark acceptance
status: completed
priority: P1
phase: 4
owner: project-maintainer
last_verified: 2026-07-17
depends_on: [RET-004]
requirements: []
contracts:
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
  - docs/05-domain-contracts/retrieval-evidence-assistant.md
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
  - docs/15-plans/stateful-local-assistant.md
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/services/embeddings/**
  - backend/app/services/evaluation/ollama_embeddings.py
  - backend/app/services/retrieval/**
  - tests/embeddings/**
  - tests/evaluation/test_ollama_embeddings.py
  - tests/retrieval/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-4-retrieval-and-evidence.md
  - docs/15-plans/stateful-local-assistant.md
  - docs/16-agent-tasks/retrieval-agent/RET-005-versioned-dense-embedding-index.md
  - docs/18-production-evidence/versioned-dense-embedding-index-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/api/**
  - backend/app/db/**
  - backend/app/services/indexing/**
  - backend/migrations/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/**
  - storage/**
dependency_changes: { allowed: false, add: [], remove: [] }
production_gates:
  - Dense artifacts are immutable canonical bytes owned by one repository and opaque index version, with checksum verification before loading.
  - Artifact identity binds the resolved embedding model name and digest, vector dimension, preprocessing version and each chunk content hash; any mismatch requires rebuild.
  - Corpus embedding is bounded and fail-closed; unavailable or malformed provider output never publishes a partial ready index.
  - Dense query retrieval accepts only a fully compatible loaded artifact and emits typed semantic candidates for the active repository/index ownership.
  - Missing, stale, corrupt or incompatible dense state disables semantic retrieval while deterministic sparse retrieval remains available.
  - Focused tests cover deterministic serialization, immutable publication, compatibility/rebuild decisions, malformed vectors, corruption and sparse fallback.
  - The frozen retrieval regression, including insufficient-evidence cases, has no regression from the accepted RET-004 baseline.
evidence_outputs:
  - docs/18-production-evidence/versioned-dense-embedding-index-report.md
---

# RET-005 — Versioned dense embedding index

## Objective

Publish and load a versioned local dense embedding artifact whose compatibility is
bound to repository/index ownership, the accepted `embeddinggemma` model identity,
vector dimension, preprocessing version and chunk content hashes. Use it as the
semantic retriever when valid, while retaining deterministic sparse retrieval for
all provider and artifact failures.

## Required commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/embeddings tests/retrieval/test_dense_embedding_index.py -q
backend\.venv\Scripts\python.exe -m pytest tests/evaluation tests/retrieval -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check -- backend/app/services/embeddings backend/app/services/evaluation/ollama_embeddings.py backend/app/services/retrieval tests/embeddings tests/evaluation/test_ollama_embeddings.py tests/retrieval docs
```

## Rollback

Remove the dense artifact builder/loader and dense search adapter, then use the
existing sparse vector service. Artifacts are additive and immutable; no database,
API, migration or dependency rollback is required.

## Verification

Completed locally on 2026-07-17. Ten focused dense-index tests pass, the canonical-LF
evaluation/retrieval regression passes 81 tests, and the final canonical-LF backend
gate passes 394 tests with 31 declared integration-profile skips. The artifact and
query adapters remain explicit composition boundaries; production worker wiring and
default configuration are not claimed by this task.
