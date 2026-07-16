---
id: RET-004
title: Benchmark Ollama dense embeddings against sparse retrieval
status: draft
priority: P1
phase: 4
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [EVA-001, AGT-007]
requirements: []
contracts: [docs/15-plans/stateful-local-assistant.md]
decisions: []
technology_docs: []
baseline_docs: []
allowed_paths: []
forbidden_paths: []
dependency_changes: { allowed: false, add: [], remove: [] }
production_gates: []
evidence_outputs: []
---

# RET-004 — Ollama dense embedding benchmark

Draft only. Compare frozen same-input sparse, Ollama dense and hybrid retrieval for quality, insufficient-evidence behavior, latency, indexing time and memory. This task may produce an adoption decision but may not replace production sparse retrieval.
