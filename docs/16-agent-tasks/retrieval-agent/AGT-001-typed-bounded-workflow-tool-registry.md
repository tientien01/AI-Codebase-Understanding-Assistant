---
id: AGT-001
title: Add typed bounded workflow and tool registry
status: completed
priority: P0
phase: 5
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [RET-003]
requirements: []
contracts:
  - docs/05-domain-contracts/retrieval-evidence-assistant.md
  - docs/05-domain-contracts/assistant/detailed-agent-workflow.md
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/services/chat/agent_workflow_service.py
  - backend/app/services/chat/workflow_contracts.py
  - backend/app/services/chat/tool_registry.py
  - tests/assistant/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-5-bounded-agent.md
  - docs/16-agent-tasks/retrieval-agent/AGT-001-typed-bounded-workflow-tool-registry.md
  - docs/18-production-evidence/agent-tool-routing-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/**
  - backend/app/db/**
  - backend/app/schemas/**
  - backend/app/services/chat/chat_service.py
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
  - Workflow request, configuration, plan, tool input/output, observation and terminal diagnostics use immutable versioned controlled contracts.
  - The tool registry is an explicit immutable allowlist and rejects unknown, duplicate, incompatible-version and repository/index-mismatched calls.
  - Deterministic routing uses exact retrieval before hybrid retrieval for eligible direct questions and never derives tool names or calls from imported content.
  - Tool-call, round, context-token and elapsed-time budgets fail closed with explicit limited/cancelled outcomes and are never increased at runtime.
  - Equivalent tool calls are deduplicated and every attempted/completed/rejected call produces a safe inspectable observation without source dumps or provider payloads.
  - Current public chat/search behavior remains schema-compatible and selected evidence remains the only context supplied to answer generation.
evidence_outputs:
  - docs/18-production-evidence/agent-tool-routing-report.md
---

# Task AGT-001 — Add typed bounded workflow and tool registry

## Context

RET-003 validates and budgets selected evidence, but the compatibility agent still stores a list of descriptive tool names while directly invoking one retrieval path. It has no versioned workflow policy, executable allowlist, typed tool observations, call deduplication, cancellation boundary or explicit workflow-budget outcome.

## Objective

Replace the descriptive compatibility plan with a deterministic typed bounded workflow and executable allowlisted retrieval-tool registry while preserving current public chat/search contracts.

## In scope

- Immutable workflow configuration/request/plan/budget/diagnostic contracts.
- Versioned typed tool input/output and safe observation contracts.
- Exact and hybrid retrieval tool adapters over existing RET-001/002 services.
- Immutable registry validation and unknown/duplicate/version/ownership rejection.
- Deterministic current-question routing, exact-to-hybrid fallback and equivalent-call deduplication.
- Tool-call/round/context-token/time/cancellation enforcement.
- Current AgentWorkflowService integration with RET-003 selected evidence.
- Positive, fallback, invalid, ownership, budget, cancellation, deterministic and imported-content regression tests.

## Out of scope

Public API/schema changes, authenticated-principal composition, dynamic LLM planning, multi-round retrieval repair, question-type sufficiency policy changes, claim extraction/support validation, citation repair, provider calls/cost accounting beyond declared zero-provider limits, persistent traces/conversations, evaluation datasets/thresholds and release qualification.

## Existing code to reuse

- Current typed query classifier, RetrievalRequest, ranked candidates and exact/hybrid retrieval adapters.
- RET-003 EvidenceService selected-context and citation projection.
- Existing AgentWorkflowResult and ChatService compatibility boundary.

## Implementation sequence

1. Define strict versioned workflow, budget and tool interchange contracts.
2. Add exact/hybrid tool adapters and immutable registry validation.
3. Add deterministic routing, budget/cancellation checks, deduplication and safe observations.
4. Integrate selected tool execution into AgentWorkflowService without public schema changes.
5. Add regression, run gates and publish evidence/baseline/status updates.

## Data/API compatibility and migration

No migration or public schema change. Existing AgentRetrievalPlan and AgentWorkflowResult remain compatibility projections. Exact eligible questions may avoid semantic/hybrid work; multi-step and exact-miss questions retain hybrid retrieval and RET-003 context selection.

## Failure, security, performance, and observability requirements

- Imported repository text is accepted only as a query/source value; it cannot name, register or invoke tools.
- Every tool call independently validates repository/index identity, declared schema/tool version and limits.
- Unknown tools, duplicate registrations, equivalent repeated calls, cancellation, timeout and exhausted budgets return stable safe diagnostics.
- Observations contain controlled IDs, counts, duration, coverage/truncation and reason codes, never absolute paths, raw source blocks, credentials, prompts or provider objects.
- Configuration values are finite/positive where required and immutable/content-addressed.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/assistant/test_bounded_workflow_tools.py -q
backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The local profile is used. PostgreSQL/Redis-only tests may retain declared skips. Exact routing proves hybrid/semantic avoidance; prompt-like repository/query text proves no unregistered tool execution. Exact outcomes and limitations are recorded in `docs/18-production-evidence/agent-tool-routing-report.md`.

## Acceptance criteria

- Workflow configuration has stable identity and invalid budgets/versions fail closed.
- Registry order/input order does not affect identity or lookup; duplicate/unknown/incompatible tools are rejected exactly.
- Eligible exact hits execute no hybrid tool, exact misses fall back once, and multi-step questions route directly to hybrid.
- Tool-call/round/time/cancellation limits stop before the next boundary and expose stable diagnostics.
- Equivalent calls execute once and observations preserve owned IDs/counts/timing without source content.
- Current workflow persists citations only from the selected RET-003 context and existing behavior regressions pass.

## Rollback

Restore direct `ranked_search` invocation in AgentWorkflowService and remove the unused workflow/tool modules and tests. No persisted schema or dependency rollback is required.

## Documentation and evidence updates

After all commands pass, publish the routing/tool report, update source/test/capability baselines and Phase 5/project status, mark this task completed, and retain AGT-002 as the next assistant task without claiming Phase 5 threshold completion.
