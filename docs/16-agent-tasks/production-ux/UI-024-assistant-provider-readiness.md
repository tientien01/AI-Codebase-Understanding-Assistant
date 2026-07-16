---
id: UI-024
title: Disclose assistant provider and fallback readiness
status: draft
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [AGT-006, AGT-007, RET-004]
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

# UI-024 — Assistant provider and readiness UX

Draft only. Render server-declared deterministic/Ollama/hybrid/fallback outcomes plus unavailable, loading, degraded and stale states. The UI may never infer provider use from configuration alone or label a deterministic fallback answer as Ollama-generated.
