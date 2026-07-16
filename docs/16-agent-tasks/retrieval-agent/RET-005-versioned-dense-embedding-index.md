---
id: RET-005
title: Add a versioned dense embedding index after benchmark acceptance
status: draft
priority: P1
phase: 4
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [RET-004]
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

# RET-005 — Versioned dense embedding index

Draft and conditional. Promote only after RET-004 records an accepted adoption gate. Bind model, dimension and preprocessing to index identity, rebuild on incompatibility, retain sparse fallback and test unavailable/stale/corrupt vector behavior.
