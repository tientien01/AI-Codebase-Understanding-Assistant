---
id: AGT-002
title: Add sufficiency, bounded repair and citation validation
status: completed
priority: P0
phase: 5
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [AGT-001]
requirements: []
contracts:
  - docs/05-domain-contracts/retrieval-evidence-assistant.md
  - docs/05-domain-contracts/assistant/detailed-agent-workflow.md
  - docs/05-domain-contracts/evidence/detailed-evidence-and-citation.md
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/services/chat/**
  - tests/assistant/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-5-bounded-agent.md
  - docs/16-agent-tasks/retrieval-agent/AGT-002-sufficiency-repair-citation-validation.md
  - docs/18-production-evidence/assistant-sufficiency-citation-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/**
  - backend/app/db/**
  - backend/app/schemas/**
  - backend/app/services/evidence/**
  - backend/app/services/retrieval/**
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
  - Sufficiency is a deterministic immutable policy by controlled question type, required support/coverage and selected current evidence, never a generic score or provider decision.
  - At most one repair round uses a controlled deterministic query, remains inside AGT-001 call/round/time/context budgets and merges only same-owner/version ranked spans deterministically.
  - Exhausted, cancelled, unchanged, empty and still-insufficient repair paths return explicit limited/insufficient outcomes with stable missing requirements.
  - Structured claims reference only selected current citations; unknown, stale, cross-owner, duplicate, scope/range and unbound citations fail closed with stable validation reasons.
  - Optional provider output is accepted only when evidence was sufficient and its declared citation IDs pass deterministic validation; otherwise deterministic fallback remains limited/grounded.
  - Public chat/search schemas and evidence identities remain compatible; no hidden reasoning, raw prompts, source dumps or provider payloads enter diagnostics.
evidence_outputs:
  - docs/18-production-evidence/assistant-sufficiency-citation-report.md
---

# Task AGT-002 — Add sufficiency, bounded repair and citation validation

## Context

AGT-001 bounds typed tool execution, but current sufficiency remains a citation-count helper, no repair follows under-covered selected context, deterministic answer claims are not structurally bound to citations, and ChatService may accept optional provider prose whenever any citation exists.

## Objective

Add deterministic question-specific sufficiency, one bounded retrieval repair and claim/citation validation, then require both evidence sufficiency and valid declared citations before accepting generated answers.

## In scope

- Immutable sufficiency decision/policy and question-specific requirements.
- One deterministic hybrid repair query/round within AGT-001 budgets.
- Deterministic same-owner/version ranked-candidate merge and final RET-003 reselection.
- Structured answer claim and citation-validation contracts.
- Current/stale/owner/index/range/selected-binding validation with stable reasons.
- AgentWorkflowService decision/repair/validation diagnostics.
- Optional LLM response citation declaration/parsing and ChatService fail-closed integration.
- Positive, under-covered, repaired, exhausted, unchanged, invalid/stale/cross-owner and provider regression tests.

## Out of scope

Public API/schema changes, authenticated-principal composition, unconstrained/dynamic planning, more than one repair, semantic entailment by a second model, persistent traces/conversations, evaluation datasets/thresholds, provider cost billing and release qualification.

## Existing code to reuse

- AGT-001 versioned workflow/tool contracts, allowlist, budgets, cancellation and safe observations.
- RET-003 selected EvidenceContext blocks and EvidenceService validation/persistence.
- Existing deterministic answer generator and optional LLMClient/ChatService compatibility boundary.

## Implementation sequence

1. Define sufficiency and structured claim/citation validation contracts.
2. Evaluate selected context by question type and implement one deterministic repair query/merge.
3. Validate deterministic claims and optional provider-declared citations against selected current evidence.
4. Integrate explicit answered/limited/insufficient behavior without public schema changes.
5. Add regression, run gates and publish evidence/baseline/status updates.

## Data/API compatibility and migration

No migration or public schema change. Internal diagnostics and LLMResult gain typed sufficiency/citation data. Provider output without valid declared citation IDs is rejected in favor of the deterministic grounded result.

## Failure, security, performance, and observability requirements

- Repair templates are controlled constants; repository/imported text cannot add tools or instructions.
- Repair checks cancellation/time/call/round budgets before and after the boundary and never raises limits.
- Candidate merge validates ownership/configuration and uses stable source-span keys/order.
- Validation never trusts provider citation paths/ranges; IDs must resolve to selected current EvidenceDTO records and exact citation metadata.
- Provider parse/validation failures expose controlled reasons only and never raw provider payloads.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/assistant/test_sufficiency_citation_repair.py -q
backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The local profile is used. PostgreSQL/Redis-only tests may retain declared skips. Results and remaining semantic/evaluation limitations are recorded in `docs/18-production-evidence/assistant-sufficiency-citation-report.md`.

## Acceptance criteria

- Exact/code, endpoint/flow/impact, architecture/onboarding and other current question types produce exact stable sufficiency actions/requirements from the same context.
- Under-covered repairable context performs no more than one non-equivalent hybrid repair and reselects a deterministic owned merged candidate set.
- Repair cancellation/budget/empty/unchanged/still-insufficient paths never answer as sufficient.
- Claims with valid selected current citations pass; unknown/stale/cross-owner/index/range/unbound/duplicate mappings fail with exact reasons.
- Optional provider prose is accepted only with sufficient agent evidence and valid declared citation IDs; invalid provider output cannot flip `evidence_sufficient` to true.
- Targeted, combined, full-backend and diff-hygiene gates pass.

## Rollback

Restore AGT-001 single-round context handling and provider compatibility behavior, then remove unused sufficiency/citation modules/tests. No schema or dependency rollback is required.

## Documentation and evidence updates

After all commands pass, publish the sufficiency/citation report, update baselines and Phase 5/project status, mark this task completed, and advance AGT-003 without claiming Phase 5 evaluation completion.
