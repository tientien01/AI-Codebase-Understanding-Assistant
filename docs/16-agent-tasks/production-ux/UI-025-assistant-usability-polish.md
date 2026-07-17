---
id: UI-025
title: Final UI polish for project management and assistant workflows
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
  - backend/app/core/config.py
  - backend/app/api/v1/routes/assistant.py
  - backend/app/services/application/use_cases.py
  - backend/app/services/chat/chat_service.py
  - backend/app/services/chat/llm_client.py
  - backend/app/services/chat/ollama_client.py
  - backend/app/services/chat/agent_workflow_service.py
  - backend/app/services/retrieval/retrieval_service.py
  - backend/app/services/repositories/repository_port.py
  - backend/app/services/repositories/repository_store.py
  - backend/app/services/repositories/production_repository_store.py
  - frontend/src/AppRoutes.tsx
  - frontend/src/App.tsx
  - frontend/src/api/client.ts
  - frontend/src/api/server.ts
  - frontend/src/components/chat/AssistantChat.tsx
  - frontend/src/components/layout/AppShell.tsx
  - frontend/src/config/navigation.ts
  - frontend/src/features/server-state/mutations.ts
  - frontend/src/hooks/useAppController.ts
  - frontend/src/hooks/useImportController.ts
  - frontend/src/pages/management/ImportPage.tsx
  - frontend/src/pages/management/ProjectsPage.tsx
  - frontend/src/pages/workspace/AssistantFullPage.tsx
  - frontend/src/pages/workspace/EvidencePage.tsx
  - frontend/src/pages/workspace/GraphPage.tsx
  - frontend/src/pages/workspace/SettingsPage.tsx
  - frontend/src/pages/workspace/SidePanels.tsx
  - frontend/src/styles/components.css
  - frontend/src/styles/pages/workspace.css
  - frontend/src/App.test.tsx
  - frontend/src/components/chat/AssistantChat.test.tsx
  - frontend/src/components/layout/AppShell.test.tsx
  - frontend/src/pages/management/ImportPage.test.tsx
  - frontend/src/pages/management/ProjectsPage.test.tsx
  - frontend/src/pages/workspace/GraphPage.test.tsx
  - README.md
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
  - Local chat may wait for a configured 15-minute Ollama generation without extending unrelated API timeouts.
evidence_outputs: []
---

# Task UI-025 — Final UI polish

## Context

The project owner authorized this bounded usability pass on 2026-07-17 after reviewing the live local assistant. Current gaps are silent provider wait time, dense raw evidence presentation, an obsolete development placeholder, no per-conversation removal control, and navigation entries the owner does not currently want exposed.

## Owner amendment — 2026-07-17

The project owner authorized one final, bounded frontend polish pass. In addition to the original assistant scope, this task may refine project-management search, filtering, sorting and pagination; import-form validation and layout; graph canvas density and inspector controls; user-focused settings presentation; global chrome alignment; and the root README. The pass remains frontend-first and must not change dependencies, database schema, migrations, provider/model settings, retrieval authority, canonical routes or security invariants.

## Objective

Make the existing grounded assistant feel responsive and easier to inspect without changing its evidence authority, model configuration, retrieval architecture, or canonical routes.

## In scope

- Pending answer feedback and duplicate-send prevention.
- Readable line-numbered evidence preview and explicit relevance metadata.
- Removal of the generic development placeholder from the Evidence side panel.
- Repository-owned per-conversation soft deletion and frontend confirmation/control.
- Prompt wording for direct, natural, appropriately detailed answers in the user's language.
- Hide Impact, Search, and Evaluation from sidebar navigation only.
- Align the browser chat timeout with the accepted 900-second local Ollama ceiling.
- Make management and workspace controls responsive, aligned and keyboard-usable at the supported viewport range.
- Make the global management search functional, show at most 25 projects per page, and provide accessible pagination and useful project sort choices.
- Require a project name and the selected import source before preview/index actions; do not prefill a misleading project name.
- Keep the dependency graph canvas dominant and remove the exposed Analyze Impact affordance without removing canonical routes.
- Simplify settings to the non-secret, user-actionable configuration summary.
- Rewrite the root README to describe the currently implemented application accurately.

## Out of scope

Streaming tokens, model changes, dense/hybrid runtime composition, graph-agent orchestration, route removal, schema migrations, dependencies, bulk history deletion, and release qualification.

## Required tests and commands

Run focused frontend assistant, graph, import, project-management and shell tests; the targeted assistant backend suite; frontend lint, TypeScript and production build; and `git diff --check`. Runtime browser review remains owner-verifiable; do not claim production evidence.

## Acceptance criteria

- One visible status row appears while chat is pending and disappears when the request settles.
- Evidence renders stable source line numbers, wraps source text, and labels why it was retrieved.
- Conversation deletion requires confirmation, rejects cross-repository IDs, invalidates cached history, and exits a deleted active route.
- Navigation omits the three requested entries without deleting their routes.
- Chat uses a dedicated browser timeout longer than the maximum configured Ollama timeout; other API requests retain their short default timeout.
- No dependency, model, schema, or migration change occurs.

## Rollback

Revert this task commit. Soft-deleted conversation records remain retained for audit and are excluded from public replay/list reads.

## Documentation and evidence updates

Update this task, the task register, and frontend UX README. Record that automated verification was intentionally deferred to owner testing.

## Implementation note

The original bounded assistant pass was implemented locally on 2026-07-17. The owner then authorized the final UI-polish amendment above. It adds functional project search, richer sorting and 25-item pagination; required import naming/source input; graph-first canvas space and no exposed Analyze Impact control; concise user-facing settings; an Evidence Viewer Code Explorer action; explicit New Chat presentation; English deterministic fallback copy; responsive UI corrections; and an accurate root README.

Focused frontend tests (59), targeted backend assistant tests (31), frontend lint, TypeScript, production build, and `git diff --check` pass. Runtime acceptance remains owner-verifiable, so this task stays `in_progress` and no production evidence is claimed.

Follow-up owner feedback raised the local Ollama ceiling from 120 to 900 seconds and assigned chat a dedicated 20-minute browser timeout. The extra five minutes cover local readiness, retrieval, validation, and persistence around a maximum-duration generation; unrelated API calls retain the 30-second default.
