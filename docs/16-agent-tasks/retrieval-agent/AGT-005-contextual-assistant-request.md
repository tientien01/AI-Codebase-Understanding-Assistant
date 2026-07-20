---
id: AGT-005
title: Ground assistant requests in explicit workspace context
status: completed
priority: P0
phase: 5
owner: project-maintainer
last_verified: 2026-07-16
depends_on: [AGT-004, UI-001, UI-009]
requirements: []
contracts:
  - docs/01-product/product-positioning.md
  - docs/01-product/scope-and-non-goals.md
  - docs/05-domain-contracts/retrieval-evidence-assistant.md
  - docs/05-domain-contracts/assistant/detailed-agent-workflow.md
  - docs/05-domain-contracts/evidence/detailed-evidence-and-citation.md
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
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
  - backend/app/services/retrieval/**
  - frontend/src/api/server.ts
  - frontend/src/AppRoutes.tsx
  - frontend/src/components/chat/**
  - frontend/src/features/server-state/mutations.ts
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/**
  - frontend/src/styles/pages/workspace.css
  - frontend/src/types/api.ts
  - frontend/src/**/*.test.ts
  - frontend/src/**/*.test.tsx
  - tests/assistant/**
  - tests/retrieval/**
  - tests/test_api_contract.py
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-5-bounded-agent.md
  - docs/16-agent-tasks/retrieval-agent/AGT-005-contextual-assistant-request.md
  - docs/18-production-evidence/assistant-context-request-report.md
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
  - docs/project-status.md
forbidden_paths:
  - backend/app/core/**
  - backend/app/db/**
  - backend/app/services/indexing/**
  - backend/app/services/repositories/**
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
  - Chat requests accept bounded typed page, file, inclusive line-range and symbol context without accepting raw source content.
  - Backend context is repository-owned, active-index-backed and validated before it can anchor retrieval; invalid context fails without crossing repository or index boundaries.
  - Code Explorer derives visible current context and lets the user remove it before sending; other pages never claim unavailable file or symbol context.
  - Context biases evidence discovery but cannot create evidence, bypass sufficiency checks or weaken citation validation.
  - Existing context-free chat requests remain compatible and deterministic fallback behavior is unchanged.
evidence_outputs:
  - docs/18-production-evidence/assistant-context-request-report.md
---

# Task AGT-005 — Ground assistant requests in explicit workspace context

## Context

The assistant currently receives only a repository ID and raw message. Code Explorer already knows the active page, file, selected line and parsed symbols, but this state is neither visible in the composer nor sent through the public chat contract. The project owner authorized this narrow read-only task on 2026-07-16.

## Objective

Carry bounded typed workspace context from the frontend to the assistant, validate it against the active indexed repository, and use valid context as a retrieval anchor while preserving evidence sufficiency, citation validation and context-free compatibility.

## In scope

- Optional request context containing page, file path, inclusive start/end line and symbol name.
- Strict length, range and shape bounds without raw source content in the request.
- Repository ownership, active-index file/range and symbol validation.
- Retrieval anchoring with validated context; the anchor cannot itself become unvalidated evidence.
- A visible removable Code Explorer context chip derived from current route and parsed file data.
- A page-only Overview context chip that never claims file, line or symbol context.
- Focused backend/API/frontend regressions and production evidence.

## Out of scope

Ollama or other provider adoption, dense embeddings, conversation replay or multi-turn memory, attachments, arbitrary user-authored context, graph/endpoint context, source editing, terminal commands, commits, PRs and release threshold acceptance.

## Existing code to reuse

- Existing `ChatRequest`, `AssistantUseCases`, `ChatService` and bounded agent workflow.
- Active repository/index validation and exact/symbol retrieval tools.
- Code Explorer route file/line state and `FileContent.symbols` ranges.
- Existing TanStack Query chat mutation and collapsible assistant drawer.

## Implementation sequence

1. Add a bounded optional public context DTO and thread it to the chat workflow.
2. Validate context against the current repository and active index, then form a deterministic retrieval anchor.
3. Derive current Code Explorer context, render a removable chip and send only the typed identifiers.
4. Add compatibility, rejection, retrieval-bias and UI request regressions.
5. Run all declared gates and record evidence and remaining limitations.

## Data/API compatibility and migration

The chat request gains one optional field, so existing clients remain valid. No response, database, migration, dependency or persisted-conversation schema changes are allowed.

## Failure, security, performance, and observability requirements

- Reject malformed, cross-repository, missing-file, out-of-range and symbol-mismatch context before retrieval anchoring.
- Never accept raw source content, evidence IDs or instructions as workspace context.
- Never scan the repository to infer a context the UI did not provide.
- Preserve bounded retrieval rounds, evidence selection, source revalidation and deterministic fallback.
- Do not persist raw provider prompts or source content in traces.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/assistant tests/retrieval tests/test_api_contract.py -q
Set-Location frontend; npx.cmd tsc -b
Set-Location frontend; npm.cmd run lint
Set-Location frontend; npm.cmd test -- --run
Set-Location frontend; npm.cmd run build
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

Record exact results in `docs/18-production-evidence/assistant-context-request-report.md`.

## Acceptance criteria

- A valid Code Explorer request carries page/file/line/symbol context and valid context measurably changes the retrieval query/selection toward that source.
- Invalid context produces a stable client error and cannot reach retrieval or provider context construction.
- The composer displays the exact context that will be sent and can remove it without changing the current source view.
- Context-free requests retain their current request shape and answer behavior.
- All required backend and frontend gates pass.

## Rollback

Remove the optional context DTO/threading and context chip while retaining the existing context-free chat contract.

## Documentation and evidence updates

Update the linked baseline, phase plan, project status, this task and the production evidence report with verified behavior only.
