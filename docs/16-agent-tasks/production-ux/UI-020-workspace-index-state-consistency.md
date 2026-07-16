---
id: UI-020
title: Keep workspace and indexing job readiness consistent
status: in_progress
priority: P1
phase: 6
owner: project-maintainer
last_verified: 2026-07-15
depends_on: [UI-002, UI-006, UI-019, IDX-003]
requirements: []
contracts:
  - docs/05-domain-contracts/indexing.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
  - docs/09-frontend-and-ux/interaction-contracts.md
allowed_paths:
  - backend/app/services/indexing/indexing_service.py
  - frontend/src/App.test.tsx
  - frontend/src/utils/repository.ts
  - tests/test_codebase_service.py
  - docs/15-plans/task-register.md
  - docs/16-agent-tasks/production-ux/UI-020-workspace-index-state-consistency.md
  - docs/18-production-evidence/workspace-index-state-consistency-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - frontend/package.json
  - frontend/package-lock.json
dependency_changes:
  allowed: false
production_gates:
  - An active repository indexing lifecycle cannot be presented as a completed usable index from an older job.
  - A terminal status bridges stale repository-list data only when its version advances the repository's recorded active version.
  - The currently active repository version remains usable when a re-index is in progress, without presenting the new candidate as activated.
  - Backend focused tests, frontend focused/full tests, lint, typecheck, build and diff hygiene pass.
evidence_outputs:
  - docs/18-production-evidence/workspace-index-state-consistency-report.md
---

# Task UI-020 — Workspace Index State Consistency

## Objective

Eliminate contradictory workspace/indexing state by binding job completion to repository activation and refusing to treat an older completed job as the active re-index attempt.

## In scope

- Normalize index-status responses against the repository lifecycle and active version.
- Preserve access to an already activated version during a later re-index while reporting the new attempt honestly.
- Restrict the frontend stale-cache bridge to a genuinely advancing successful version.
- Add focused backend and frontend regressions for the conflicting state shown by the workspace.

## Out of scope

- Queue, lease, schema or index pipeline redesign.
- New API fields, dependencies or route changes.
- Changes to graph, retrieval or indexing algorithms.

## Required verification

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/test_codebase_service.py -q
backend\.venv\Scripts\python.exe -m pytest tests/jobs/test_job_queue.py -q
Set-Location frontend
npm.cmd test -- --run src/App.test.tsx
npm.cmd test -- --run
npm.cmd run lint
npx.cmd tsc -b --pretty false
npm.cmd run build
Set-Location ..
git diff --check -- backend/app/services/indexing/indexing_service.py frontend/src/App.test.tsx frontend/src/utils/repository.ts tests/test_codebase_service.py docs/15-plans/task-register.md docs/16-agent-tasks/production-ux/UI-020-workspace-index-state-consistency.md docs/18-production-evidence/workspace-index-state-consistency-report.md
```

## Acceptance criteria

- When repository lifecycle is `indexing`, an older completed job at the repository's existing active version cannot make the UI claim that the new attempt completed.
- A completed job may bridge stale repository data only when its positive version is greater than the repository's recorded active version.
- First-index completion still bridges a stale repository record whose active version is absent/zero.
- Existing successful index and re-index behavior remains covered.

## Current verification state

Implemented and locally verified on 2026-07-15. The focused backend suite passes 28 tests; the queue boundary passes its 2 environment-independent tests while 3 PostgreSQL/Redis integration cases remain skipped because `TEST_POSTGRES_ADMIN_URL` and `TEST_REDIS_URL` are unavailable. All 88 frontend tests, lint, TypeScript and the production build pass. The task remains `in_progress` until the declared integration prerequisites are available and those skipped cases execute.
