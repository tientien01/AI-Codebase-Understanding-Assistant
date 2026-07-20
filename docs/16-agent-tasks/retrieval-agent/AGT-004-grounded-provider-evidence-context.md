---
id: AGT-004
title: Ground optional provider answers in validated source evidence
status: completed
priority: P0
phase: 5
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [AGT-002, AGT-003]
requirements: []
contracts:
  - docs/01-product/product-positioning.md
  - docs/01-product/scope-and-non-goals.md
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
  - tests/test_service_boundaries.py
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-5-bounded-agent.md
  - docs/16-agent-tasks/retrieval-agent/AGT-004-grounded-provider-evidence-context.md
  - docs/18-production-evidence/assistant-provider-evidence-context-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/**
  - backend/app/core/**
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
  - The optional provider receives selected validated source content, stable evidence identity and safe source locators rather than citation metadata alone.
  - Provider context remains bound to one repository and active index and preserves whole evidence spans within the existing assistant context-token budget.
  - User-selected evidence is re-read from the current indexed source, hash/range/security validated and rejected from provider context when it is stale, changed, blocked or over budget.
  - Imported source is delimited as untrusted data and cannot add instructions or tools; provider output still cannot create evidence or citation identities.
  - Provider absence, context rejection, timeout-compatible null results and invalid citation declarations retain the deterministic grounded fallback.
  - Provider source content and prompts never enter public responses, persistence diagnostics or privacy-safe traces.
evidence_outputs:
  - docs/18-production-evidence/assistant-provider-evidence-context-report.md
---

# Task AGT-004 — Ground optional provider answers in validated source evidence

## Context

The bounded assistant already selects whole validated evidence blocks and rejects provider answers whose declared citations are invalid. The optional provider boundary currently receives only evidence IDs, file locations and symbols, so a configured provider cannot inspect the source content that those citations represent. The project owner authorized this narrow read-only task on 2026-07-16 and explicitly retained source editing, command execution, commit generation and pull-request automation as non-goals.

## Objective

Pass only selected, validated, token-budgeted source evidence content to the optional provider, while preserving deterministic fallback, citation validation, trace privacy and the read-only product boundary.

## In scope

- An immutable internal provider-evidence contract containing owned evidence identity, safe source locator, support metadata, token estimate and exact selected content.
- Projection of RET-003 selected evidence blocks into provider context without re-reading unrelated repository files.
- Current-source revalidation and bounded source-range reads for the existing user-selected-evidence chat path.
- A provider prompt that clearly delimits imported source as untrusted data and restricts returned citation IDs to supplied evidence.
- Fail-closed provider avoidance for empty, invalid, stale, changed, blocked, mixed-owner/version or over-budget context.
- Focused prompt/context, provider fallback, citation and trace-privacy regression tests.

## Out of scope

Frontend/context-chip changes, public API/schema changes, conversation history APIs, new retrieval/index artifacts, embeddings or rerankers, model/provider adoption, semantic answer judging, autonomous editing, terminal commands, tests executed from imported repositories, commits, PRs and release threshold acceptance.

## Existing code to reuse

- RET-003 `ValidatedEvidenceBlock` and whole-span context-token budget.
- AGT-002 sufficiency and selected/current citation validation.
- AGT-003 privacy-safe trace persistence and deterministic fallback behavior.
- Current `LLMClient` provider adapter and `ChatService` orchestration boundary.

## Implementation sequence

1. Add the strict internal provider-evidence/context projection contract.
2. Carry selected evidence context through the bounded workflow without exposing it publicly or persisting source content in traces.
3. Revalidate and range-read current source for the selected-evidence path, then call the provider only when the complete required context remains valid and within budget.
4. Render a delimited untrusted-source prompt and retain provider citation parsing/validation.
5. Add regressions, run all gates and record exact evidence and remaining provider-quality limitations.

## Data/API compatibility and migration

No public request/response, persistence schema, migration or dependency change. Provider method inputs change only at the internal chat boundary. Conversation messages, citations and trace event schemas remain unchanged.

## Failure, security, performance and observability requirements

- Never scan or send the whole repository; source reads are limited to selected validated inclusive ranges.
- Reject provider context on owner/index/hash/range/blocked-policy mismatch or when all required whole blocks do not fit the configured budget.
- Delimit source content as untrusted data and state that it cannot issue instructions.
- Never log or persist source blocks, raw provider prompts, provider payloads, secrets or hidden reasoning.
- Provider failures and rejected output return the existing deterministic answer without weakening evidence sufficiency.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/assistant/test_provider_evidence_context.py -q
backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check -- backend/app/services/chat tests/assistant tests/test_service_boundaries.py docs
```

The local profile is mandatory. Existing declared PostgreSQL/Redis integration-profile skips may remain. The report records exact counts and makes no real-provider quality, latency, cost or release-readiness claim.

## Acceptance criteria

- A configured-provider request includes the exact content of every selected validated evidence block and no unrelated source content.
- Evidence identity/path/range/symbol/support metadata remains paired with each delimited content block.
- Empty, changed, stale, blocked, cross-owner/version, invalid-range and over-budget contexts do not reach the provider.
- Prompt-like text inside imported source remains delimited data and cannot alter the tool allowlist or citation set.
- Invalid/unknown/duplicate/empty provider citation declarations continue to fall back deterministically.
- Trace and persistence regressions prove source content and raw prompts are not stored.
- Targeted, combined, full-backend and diff-hygiene gates pass.

## Rollback

Remove the internal provider-evidence projection and restore provider avoidance or the prior citation-metadata-only compatibility call. No data or schema rollback is required.

## Documentation and evidence updates

After all gates pass, publish `assistant-provider-evidence-context-report.md`, update the assistant source/test/capability baselines and Phase 5 limitation, mark this task completed, and retain real-provider qualification and frontend contextual assistant work for separately authorized tasks.

## Verification

Completed locally on 2026-07-16. The focused provider-context gate passes 7 tests, the combined assistant/evidence/retrieval/service gate passes 121 tests, and a canonical-LF disposable local checkout passes the full backend suite with 342 passed and 31 declared integration-profile skips. Diff hygiene passes. Exact results, the Windows CRLF fixture condition and remaining real-provider/frontend limitations are recorded in `docs/18-production-evidence/assistant-provider-evidence-context-report.md`.
