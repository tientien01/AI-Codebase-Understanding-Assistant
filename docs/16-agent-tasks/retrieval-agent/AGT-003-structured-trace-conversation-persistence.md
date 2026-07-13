---
id: AGT-003
title: Persist structured traces and conversations
status: completed
priority: P0
phase: 5
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [AGT-002, DAT-003]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/05-domain-contracts/assistant/detailed-agent-workflow.md
  - docs/05-domain-contracts/evidence/detailed-evidence-and-citation.md
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
  - docs/07-security/threat-model.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/db/models.py
  - backend/app/services/application/container.py
  - backend/app/services/chat/**
  - backend/app/services/repositories/repository_port.py
  - backend/app/services/repositories/repository_store.py
  - backend/app/services/repositories/production_repository_store.py
  - tests/assistant/**
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-5-bounded-agent.md
  - docs/16-agent-tasks/retrieval-agent/AGT-003-structured-trace-conversation-persistence.md
  - docs/18-production-evidence/assistant-trace-persistence-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/api/**
  - backend/app/db/production_models/**
  - backend/app/schemas/**
  - backend/app/services/evidence/**
  - backend/app/services/retrieval/**
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
  - A successful chat turn atomically persists its conversation, ordered messages, structured claims/citations, trace summary and ordered controlled events.
  - Local SQLite and production PostgreSQL adapters preserve repository/index ownership and return the same replay read model.
  - Trace payloads use an explicit allowlist and never contain raw prompts, source excerpts, provider payloads, hidden reasoning, credentials or imported instructions.
  - User and assistant message content is length-bounded and deterministically redacts credential-shaped values before persistence.
  - Persistence failure is fail-closed and cannot return an answer whose durable trace is missing or partially written.
  - Replay is repository-scoped, ordered deterministically and exposes only redacted messages plus controlled trace metadata.
  - Existing public chat/search schemas, AGT-002 sufficiency behavior and production schema remain compatible.
evidence_outputs:
  - docs/18-production-evidence/assistant-trace-persistence-report.md
---

# Task AGT-003 — Persist structured traces and conversations

## Context

AGT-002 produces bounded, evidence-validated answers and typed diagnostics, while conversations and agent events remain transient. DAT-001/DAT-002 already define production conversation, message, claim, citation, trace and trace-event tables, but the application has no persistence port or local-profile equivalent for them.

## Objective

Persist each completed assistant turn as an ownership-scoped, privacy-safe structured trace and provide a deterministic internal replay read model across local SQLite and production PostgreSQL profiles.

## In scope

- Immutable conversation/message/claim/citation/trace/event persistence contracts.
- Controlled event types and allowlisted payloads derived from AGT-001/AGT-002 decisions.
- Deterministic credential redaction and message size bounds.
- Atomic local SQLite and production PostgreSQL writes using the existing schema.
- Repository-scoped replay with stable event and message ordering.
- ChatService composition and fail-closed persistence behavior.
- Privacy, ownership, rollback, ordering and compatibility tests.

## Out of scope

Public history/replay endpoints, frontend conversation UI, authenticated-principal delivery, schema migrations, free-form chain-of-thought storage, raw prompt/provider/source persistence in traces, retention scheduling, evaluation datasets/thresholds, semantic entailment and release qualification.

## Existing code to reuse

- AGT-001/AGT-002 workflow result, controlled diagnostics, sufficiency and citation-validation contracts.
- Existing `RepositoryStorePort`, local `RepositoryStore` transaction pattern and production `ProductionRepositoryStore` session boundary.
- Accepted production conversation/claim/citation/trace tables from DAT-001/DAT-002.
- Existing evidence identities and production index-version mapping.

## Implementation sequence

1. Define immutable persisted-turn and replay contracts with controlled event payload construction/redaction.
2. Add local SQLite models and atomic repository-store persistence/replay.
3. Map the same aggregate to existing production tables without schema changes.
4. Integrate ChatService so returned completed answers have a durable trace.
5. Add privacy/integration regression tests, run gates and publish evidence/baseline/status updates.

## Data/API compatibility and migration

The accepted production schema is unchanged. Local SQLite creates additive compatibility tables through existing metadata initialization. Public request/response schemas remain unchanged; generated internal identities use accepted opaque prefixes, while repository and evidence identities retain their current contracts.

## Failure, security, performance, and observability requirements

- One store call owns the transaction; any failed row rolls back the whole turn.
- Every child row repeats or validates repository/conversation/trace ownership through the adapter boundary.
- Trace event payload keys and values are bounded controlled metadata, never copied arbitrary diagnostics.
- Credential-shaped message fragments are replaced with a stable redaction marker before write and replay.
- Replay filters by repository and trace ID and sorts messages/events by sequence rather than database incidental order.
- No imported repository content is executed or interpreted as instructions.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/assistant/test_trace_persistence.py -q
backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

The local profile is mandatory. Existing declared PostgreSQL/Redis-only skips may remain, but production adapter mapping and transactional behavior must have deterministic tests that do not require weakening environment gates. Results are recorded in `docs/18-production-evidence/assistant-trace-persistence-report.md`.

## Acceptance criteria

- One successful ChatService answer produces one conversation, two ordered messages, one trace, controlled ordered events and persisted claims/citations matching the returned answer.
- Trace replay for the owning repository returns the same redacted ordered aggregate; a different repository receives no record.
- Secret-shaped input/provider text and raw source content do not appear in trace payloads or persisted/replayed messages.
- Simulated persistence failure leaves no partial turn and the ChatService does not return a successful answer.
- Local and production adapters map the same ownership, index version, status, claims, citations and event sequence semantics.
- Existing AGT-002 tests, combined service regression, full backend suite and diff-hygiene gates pass.

## Rollback

Remove the ChatService persistence call, trace contracts, additive local tables and adapter methods. The existing production tables remain unused, so no production migration rollback is required.

## Documentation and evidence updates

After all commands pass, publish the trace persistence report, update baselines and Phase 5/project status, mark this task completed, and advance the next authorized task without claiming Phase 5 evaluation or release completion.
