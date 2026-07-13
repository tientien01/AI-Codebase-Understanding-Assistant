---
id: RET-003
title: Add validated evidence selector and token-budget context
status: completed
priority: P0
phase: 4
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [RET-002]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/05-domain-contracts/retrieval-evidence-assistant.md
  - docs/05-domain-contracts/evidence/detailed-evidence-and-citation.md
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
  - backend/app/services/evidence/**
  - backend/app/services/retrieval/retrieval_service.py
  - backend/app/services/chat/agent_workflow_service.py
  - tests/evidence/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-4-retrieval-and-evidence.md
  - docs/16-agent-tasks/retrieval-agent/RET-003-evidence-selector-and-token-budget-context.md
  - docs/18-production-evidence/evidence-context-budget-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/**
  - backend/app/db/**
  - backend/app/schemas/**
  - backend/app/services/chat/chat_service.py
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
  - Candidate promotion validates repository/index ownership, current freshness, canonical source existence, raw source hash, inclusive range, blocked/skipped policy and controlled support before evidence creation.
  - Evidence IDs are opaque, immutable, repository/version/source/hash/range bound, and repeated selection is idempotent.
  - Selection records every selected and rejected candidate ID with stable reason codes and merges no cross-source or cross-version evidence.
  - Selection prioritizes question-type coverage, exact named targets, support strength, source diversity and ranked order deterministically.
  - Context records repository/index/ranking IDs, ordered whole evidence blocks, per-block estimates, omitted summary, budget, used tokens, status, truncation and missing requirements.
  - Context never truncates inside an evidence/citation span; an oversized required block yields an insufficient result.
  - Empty, invalid, stale, blocked, over-budget and under-covered inputs preserve explicit insufficient/limited outcomes.
evidence_outputs:
  - docs/18-production-evidence/evidence-context-budget-report.md
---

# Task RET-003 — Add validated evidence selector and token-budget context

## Context

RET-002 ranks owned typed candidates, but the current agent converts every hybrid match directly into persisted evidence. It does not validate current source hash/security/range before promotion, record selection rejections, or construct an inspectable whole-span context within a token budget.

## Objective

Add a deterministic evidence selector and token-budget context builder over RET-002 ranked candidates, persist only selected validated support, and use the selected context in the current single-round compatibility workflow.

## In scope

- Immutable selection policy, validated evidence block, rejection, omission and context-result contracts.
- Current repository/index/source/hash/range/blocked/support eligibility validation.
- Opaque deterministic evidence identity bound to validated immutable inputs.
- Question-type/exact/support/diversity/rank selection priority.
- Whole-block token estimation, max-evidence and budget handling without citation-span truncation.
- Stable selected/rejected IDs, reason codes, omitted summary, status/truncation/missing requirements.
- EvidenceService persistence/citation projection for selected blocks.
- Retrieval ranked-result access and current agent workflow integration.
- Positive, invalid, stale, blocked, hash/range, diversity, deterministic, oversized, partial-budget and insufficient regressions.

## Out of scope

Public schema/API/frontend changes, authenticated principal implementation, historical-index selection, claim extraction/support validation, citation-to-claim mapping, multi-round repair, persistent structured traces, provider prompting, semantic tokenizers, evaluation datasets/thresholds, and release readiness.

## Existing code to reuse

- RET-001 owned candidates and RET-002 ranked candidates/config identity.
- Current `RepositoryState`, `FileRecord`, chunk content/hash, skipped/security records and EvidenceService persistence port.
- Existing CitationDTO/EvidenceDTO compatibility output and agent insufficient-evidence behavior.

## Implementation sequence

1. Define strict selection/context contracts and stable evidence identity/reason codes.
2. Validate ownership, freshness, source/hash/range/security/support and order eligible evidence.
3. Select whole blocks within evidence/token budgets and compute status/omission/missing requirements.
4. Persist selected evidence idempotently, project citations and integrate the current single-round workflow.
5. Add evidence/budget regression, run gates and publish evidence/baseline/status updates.

## Data/API compatibility and migration

No migration or public schema change. Current search/chat response schemas remain unchanged. Agent citations are now created only from selected validated context; deterministic evidence IDs may replace per-call UUIDs for that path. Existing direct search compatibility remains available.

## Failure, security, performance, and observability requirements

- Validation reads only declared indexed source files and never executes/imports/builds/tests source or follows repository instructions.
- Host absolute paths never enter evidence IDs, context records, rejection details or persistence metadata.
- Cross-owner/version inputs fail closed; per-candidate source/hash/range/security failures are rejected with stable safe codes.
- Policy rejects non-positive budgets/limits/estimators and uncontrolled support values.
- Selection and omission ordering is deterministic under ranked-input reordering; source content is represented only by selected bounded blocks/safe previews.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/evidence/test_evidence_context.py -q
backend\.venv\Scripts\python.exe -m pytest tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The local profile is used. PostgreSQL/Redis-only tests may retain declared skips. The evidence regression includes insufficient-evidence and whole-span budget cases; exact reason/status/budget results and limitations are recorded in `docs/18-production-evidence/evidence-context-budget-report.md`.

## Acceptance criteria

- Valid current source candidates produce stable evidence IDs and repeatable byte-equivalent context records.
- Cross-owner/version fails closed; missing/changed/blocked/out-of-range candidates are rejected with exact stable codes.
- Selected blocks remain whole, budget totals are exact under the declared estimator, and oversized required evidence yields insufficient.
- Diversity/rank/input-order cases produce deterministic selected/rejected order and omission counts.
- Persisted selected evidence retains repository/version/source/range/hash/support/ranking/selection metadata and citations reference only selected IDs.
- Current agent uses selected citations and exposes missing requirements when context is insufficient.
- Targeted evidence, retrieval/service regression, full backend and diff-hygiene gates pass.

## Rollback

Restore direct hybrid-match citation creation in the compatibility workflow and remove the unused selector/context module/tests/docs. Deterministic evidence upserts require no migration rollback.

## Documentation and evidence updates

After all commands pass, publish the evidence/context budget report, update source/test/capability baselines and Phase 4 status, mark this task completed, and advance the next candidate to `AGT-001` while retaining `EVA-001` as separate evaluation work.
