---
id: UI-024
title: Disclose assistant provider and fallback readiness
status: completed
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-17
depends_on: [AGT-006, AGT-007, RET-004]
requirements: []
contracts: [docs/15-plans/stateful-local-assistant.md]
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/schemas/assistant.py
  - backend/app/services/chat/chat_service.py
  - tests/assistant/**
  - frontend/src/components/chat/**
  - frontend/src/hooks/useAppController.ts
  - frontend/src/types/api.ts
  - frontend/src/**/*.test.tsx
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/15-plans/stateful-local-assistant.md
  - docs/16-agent-tasks/production-ux/UI-024-assistant-provider-readiness.md
  - docs/18-production-evidence/assistant-provider-readiness-ui-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/migrations/**
  - frontend/package.json
  - frontend/package-lock.json
dependency_changes: { allowed: false, add: [], remove: [] }
production_gates:
  - Chat responses declare generation and retrieval outcomes; clients never infer them from configuration.
  - Accepted Ollama output is labeled Ollama, provider failure is labeled deterministic fallback, and insufficient evidence is not mislabeled as provider failure.
  - The UI renders declared Ollama, deterministic, fallback, sparse and hybrid states and preserves truthful unknown state for replay without declarations.
  - Stale conversation and loading/error disclosures remain intact.
evidence_outputs:
  - docs/18-production-evidence/assistant-provider-readiness-ui-report.md
---

# UI-024 — Assistant provider and readiness UX

## Objective

Render server-declared deterministic/Ollama/provider/fallback generation and
sparse/hybrid retrieval outcomes on assistant messages without inferring use from
configuration. Preserve existing loading, error, insufficient-evidence and stale
conversation disclosures.

## Verification

Completed locally on 2026-07-17. Provider-focused backend tests pass 26, the full
assistant suite passes 65, and frontend lint, all 115 tests across 17 files, TypeScript
production compilation and Vite build pass. The UI labels only outcomes carried by
the current server response; historic messages without declarations remain unlabeled.
