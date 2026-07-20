---
id: AGT-006
title: Deliver repository-owned conversation replay and bounded memory
status: completed
priority: P0
phase: 5
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [AGT-003, AGT-005, UI-001, UI-002]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/05-domain-contracts/assistant/detailed-agent-workflow.md
  - docs/05-domain-contracts/evidence/detailed-evidence-and-citation.md
  - docs/07-security/threat-model.md
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/api/v1/routes/assistant.py
  - backend/app/schemas/assistant.py
  - backend/app/schemas/api.py
  - backend/app/services/application/use_cases.py
  - backend/app/services/chat/**
  - backend/app/services/repositories/repository_port.py
  - backend/app/services/repositories/repository_store.py
  - backend/app/services/repositories/production_repository_store.py
  - frontend/src/AppRoutes.tsx
  - frontend/src/api/server.ts
  - frontend/src/components/chat/**
  - frontend/src/features/server-state/**
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/AssistantFullPage.tsx
  - frontend/src/routing/**
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - frontend/src/**/*.test.ts
  - frontend/src/**/*.test.tsx
  - tests/assistant/**
  - tests/persistence/**
  - tests/test_api_contract.py
  - tests/test_codebase_service.py
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-5-bounded-agent.md
  - docs/15-plans/stateful-local-assistant.md
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/retrieval-agent/AGT-006-stateful-conversation-foundation.md
  - docs/18-production-evidence/assistant-stateful-conversation-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/core/**
  - backend/app/db/**
  - backend/app/services/evidence/**
  - backend/app/services/indexing/**
  - backend/app/services/retrieval/**
  - backend/migrations/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/package.json
  - frontend/package-lock.json
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Repository-owned conversation list and replay APIs return bounded deterministic summaries/messages and never expose another repository's conversation.
  - Frontend retains the returned conversation ID, sends it on subsequent turns, deep-links/replays an owned conversation after refresh and starts a new conversation without relabeling local cache as history.
  - Backend projects only a bounded recent conversation window into retrieval/provider intent context; conversation text never becomes evidence or bypasses sufficiency/citation validation.
  - Unknown, malformed, cross-repository and stale-index conversation use fail with stable safe states; context-free first-turn chat remains compatible.
  - Persisted messages remain redacted and bounded; history endpoints do not expose traces, hidden reasoning, provider payloads or raw source.
evidence_outputs:
  - docs/18-production-evidence/assistant-stateful-conversation-report.md
---

# AGT-006 — Stateful conversation foundation

## Context

AGT-003 persists repository-owned conversations/messages and internal trace replay, but no public history read model exists. The frontend discards returned conversation IDs, labels local cache slicing as history, and cannot restore a conversation after refresh. Backend answering also ignores prior turns.

## Objective

Make conversations durable and replayable end to end, and use a bounded deterministic recent-turn projection to resolve follow-up intent without treating conversation text as repository evidence.

## In scope

- Bounded repository-owned conversation summary/list and message replay DTOs/APIs.
- Stable conversation ID retention across sends, full Assistant deep links, refresh and history selection.
- Truthful New Chat and History behavior backed by server state.
- Deterministic recent-turn memory selection with explicit turn/token limits.
- Memory-assisted retrieval/provider question context separated from validated evidence.
- Stale-index disclosure/fail-safe behavior and focused API/persistence/frontend regressions.

## Out of scope

Ollama/provider adoption, dense embeddings, provider readiness UI, semantic conversation summarization, message editing, branching, sharing, attachments, source modification, migrations, retention scheduling and release qualification.

## Existing code to reuse

- AGT-003 conversation/message persistence and redaction contracts.
- Repository store local/production adapters and accepted conversation/message tables.
- Existing assistant deep-link route, TanStack Query ownership and chat mutation.
- AGT-005 workspace context and AGT-002/004 evidence/provider safeguards.

## Implementation sequence

1. Add bounded conversation summary/transcript/memory contracts and owned store reads.
2. Expose list/replay APIs and stable error mapping without exposing traces.
3. Load recent bounded memory before retrieval, preserving evidence and citation authority.
4. Retain conversation identity in frontend server state; implement real New Chat, History and deep-link replay.
5. Run all gates, publish evidence and update baselines/status.

## Data/API compatibility and migration

Existing tables are reused without migration. New read endpoints and response DTOs are additive. Chat without `conversation_id` remains a valid first turn; a supplied ID must already belong to the current repository.

## Failure, security, performance, and observability requirements

- List and replay are bounded, deterministically ordered and repository scoped.
- Memory uses a fixed recent-turn/token policy and records only safe count/budget metadata in diagnostics.
- Previous assistant text is conversational context, never evidence; current answers still require current-index citations.
- Historical index identity is disclosed and cannot silently support a current technical claim.
- No raw trace events, prompts, provider payloads, source excerpts or hidden reasoning enter history DTOs.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/persistence tests/test_api_contract.py -q
Set-Location frontend; npx.cmd tsc -b
Set-Location frontend; npm.cmd run lint
Set-Location frontend; npm.cmd test -- --run
Set-Location frontend; npm.cmd run build
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

## Acceptance criteria

- Two follow-up sends use one server-issued conversation ID and the second retrieval query contains a bounded prior-turn projection.
- Refreshing `/repositories/:repositoryId/assistant/:conversationId` replays the same ordered redacted messages.
- History is server-backed; New Chat clears active identity without deleting prior history.
- Cross-repository/unknown IDs and over-budget histories fail or truncate with stable tested behavior.
- Context-free first-turn chat, workspace context, evidence sufficiency, citation validation and provider fallback regressions pass.

## Rollback

Remove public history APIs/frontend reads and disable memory projection while retaining already persisted conversation rows and context-free chat behavior.

## Documentation and evidence updates

Publish the AGT-006 evidence report, update linked baselines/Phase 5/project status, and keep AGT-007/RET-004/RET-005/UI-024 draft until separately promoted.
