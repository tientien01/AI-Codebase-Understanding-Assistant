---
id: BUG-002
title: Prevent duplicate symbol IDs and failed index activation drift
status: completed
priority: P0
phase: 2
owner: project-maintainer
last_verified: 2026-07-17
depends_on: [IDX-003]
requirements: []
contracts:
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/services/code_analysis/cpg/emitter.py
  - backend/app/services/code_analysis/stable_ids.py
  - backend/app/services/parsing/javascript_parser.py
  - backend/app/services/parsing/tree_sitter_parser.py
  - backend/app/services/parsing/source_fallback_parser.py
  - backend/app/services/indexing/indexing_service.py
  - backend/app/services/repositories/repository_store.py
  - tests/intelligence/**
  - tests/indexing/**
  - tests/test_code_analysis.py
  - tests/test_codebase_service.py
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/indexing/BUG-002-duplicate-symbol-index-activation.md
  - docs/18-production-evidence/duplicate-symbol-index-hotfix-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/api/**
  - backend/app/db/**
  - backend/migrations/**
  - frontend/**
  - storage/**
dependency_changes: { allowed: false, add: [], remove: [] }
production_gates:
  - Repeated same-name definitions receive deterministic unique symbol IDs without weakening ordinary line-shift identity.
  - Duplicate symbol primary keys are rejected before opening a persistence transaction.
  - A failed index persistence never activates the candidate in memory and records a failed job/status.
  - The previously active index remains queryable after failed re-index persistence.
  - A legacy completed-but-unpublished first candidate is repaired to failed and can be retried.
evidence_outputs:
  - docs/18-production-evidence/duplicate-symbol-index-hotfix-report.md
---

# BUG-002 — Duplicate symbol index activation hotfix

Fix the reproduced SQLite `symbol_records.id` uniqueness failure and the resulting
in-memory/database active-index divergence that caused chat persistence to return 500.

## Verification

Completed locally on 2026-07-17. Seven focused duplicate/publish/recovery regressions pass and
the combined code-analysis/indexing-service gate passes 50 tests. Repeated definitions
remain deterministic, duplicate persistence fails before transaction work, and a
failed candidate commit preserves the previous active in-memory version.
