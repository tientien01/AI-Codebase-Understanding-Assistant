---
id: AGT-007
title: Add an optional grounded Ollama chat provider
status: draft
priority: P0
phase: 5
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [AGT-004, AGT-006]
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

# AGT-007 — Ollama grounded chat provider

Draft only. Add an explicit local Ollama adapter, model/base-URL validation, bounded timeout, health/readiness and deterministic evidence-backed fallback. Promotion requires exact security/network configuration, model qualification cases and evidence destinations. It must not add embeddings or weaken AGT-004 provider context/citation checks.
