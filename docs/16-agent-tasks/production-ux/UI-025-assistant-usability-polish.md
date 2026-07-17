---
id: UI-025
title: Polish assistant feedback, evidence, and conversation controls
status: in_progress
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-17
depends_on: [AGT-006, AGT-007, UI-024]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/15-plans/stateful-local-assistant.md
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
allowed_paths:
  - backend/app/api/v1/routes/assistant.py
  - backend/app/services/application/use_cases.py
  - backend/app/services/chat/chat_service.py
  - backend/app/services/chat/llm_client.py
  - backend/app/services/repositories/repository_port.py
  - backend/app/services/repositories/repository_store.py
  - backend/app/services/repositories/production_repository_store.py
  - frontend/src/AppRoutes.tsx
  - frontend/src/api/server.ts
  - frontend/src/components/chat/AssistantChat.tsx
  - frontend/src/config/navigation.ts
  - frontend/src/features/server-state/mutations.ts
  - frontend/src/hooks/useAppController.ts
  - frontend/src/pages/workspace/AssistantFullPage.tsx
  - frontend/src/pages/workspace/EvidencePage.tsx
  - frontend/src/pages/workspace/SidePanels.tsx
  - frontend/src/styles/pages/workspace.css
  - docs/09-frontend-and-ux/README.md
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/production-ux/UI-025-assistant-usability-polish.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/migrations/**
  - frontend/package.json
  - frontend/package-lock.json
dependency_changes: { allowed: false, add: [], remove: [] }
production_gates:
  - Chat visibly reports a pending response while one request is active.
  - Evidence source lines and retrieval context remain readable without changing evidence identity.
  - An owned conversation can be removed from visible history through a confirmed action.
  - Assistant prompts request direct natural-language explanations while preserving citation validation.
  - Impact, Search, and Evaluation remain deep-linkable but are hidden from workspace navigation.
evidence_outputs: []
---

# Task UI-025 — Assistant usability polish

## Context

The project owner authorized this bounded usability pass on 2026-07-17 after reviewing the live local assistant. Current gaps are silent provider wait time, dense raw evidence presentation, an obsolete development placeholder, no per-conversation removal control, and navigation entries the owner does not currently want exposed.

## Objective

Make the existing grounded assistant feel responsive and easier to inspect without changing its evidence authority, model configuration, retrieval architecture, or canonical routes.

## In scope

- Pending answer feedback and duplicate-send prevention.
- Readable line-numbered evidence preview and explicit relevance metadata.
- Removal of the generic development placeholder from the Evidence side panel.
- Repository-owned per-conversation soft deletion and frontend confirmation/control.
- Prompt wording for direct, natural, appropriately detailed answers in the user's language.
- Hide Impact, Search, and Evaluation from sidebar navigation only.

## Out of scope

Streaming tokens, model changes, dense/hybrid runtime composition, graph-agent orchestration, route removal, schema migrations, dependencies, bulk history deletion, and release qualification.

## Required tests and commands

The owner explicitly requested no automated test/build run for this rapid local pass and will perform runtime verification. Perform only static diff review and `git diff --check`; do not claim verified production evidence.

## Acceptance criteria

- One visible status row appears while chat is pending and disappears when the request settles.
- Evidence renders stable source line numbers, wraps source text, and labels why it was retrieved.
- Conversation deletion requires confirmation, rejects cross-repository IDs, invalidates cached history, and exits a deleted active route.
- Navigation omits the three requested entries without deleting their routes.
- No dependency, model, schema, or migration change occurs.

## Rollback

Revert this task commit. Soft-deleted conversation records remain retained for audit and are excluded from public replay/list reads.

## Documentation and evidence updates

Update this task, the task register, and frontend UX README. Record that automated verification was intentionally deferred to owner testing.

## Implementation note

Implemented locally on 2026-07-17. The requested source and documentation changes are complete, and static `git diff --check` passes. Automated frontend/backend tests and production build were intentionally not run at the owner's request; runtime acceptance remains owner-verifiable, so this task stays `in_progress` and no production evidence is claimed.
