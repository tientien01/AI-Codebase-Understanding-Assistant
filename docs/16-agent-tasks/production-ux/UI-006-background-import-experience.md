---
id: UI-006
title: Make GitHub acquisition explicit, staged, and non-blocking
status: completed
priority: P0
phase: 6
owner: project-maintainer
last_verified: 2026-07-17
depends_on: [UI-002, SEC-001]
requirements: []
contracts:
  - docs/09-frontend-and-ux/interaction-contracts.md
  - docs/09-frontend-and-ux/page-contracts/detailed-workspace-ux.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/api/v1/routes/import_sessions.py
  - backend/app/schemas/api.py
  - backend/app/schemas/imports.py
  - backend/app/services/index_models.py
  - backend/app/services/ingestion/archive_service.py
  - backend/app/services/ingestion/import_session_service.py
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - frontend/src/api/server.ts
  - frontend/src/api/upload.ts
  - frontend/src/api/upload.test.ts
  - frontend/src/features/server-state/keys.ts
  - frontend/src/features/server-state/queries.ts
  - frontend/src/hooks/useAppController.ts
  - frontend/src/hooks/useImportController.ts
  - frontend/src/hooks/useImportController.test.tsx
  - frontend/src/AppRoutes.tsx
  - frontend/src/components/common/ui.tsx
  - frontend/src/pages/management/ImportPage.tsx
  - frontend/src/pages/management/ImportPage.test.tsx
  - frontend/src/pages/management/IndexingPage.tsx
  - frontend/src/styles/pages/import.css
  - frontend/src/types/api.ts
  - tests/test_api_contract.py
  - tests/test_codebase_service.py
  - tests/security/test_import_acquisition_security.py
  - docs/16-agent-tasks/production-ux/UI-006-background-import-experience.md
  - docs/18-production-evidence/background-import-ux-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/db/**
  - backend/migrations/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Pasting a GitHub URL does not start network acquisition without an explicit action.
  - GitHub acquisition returns a session immediately and exposes safe server-owned stages until preview is ready or terminally failed.
  - The Import page remains visible with elapsed time, stage text, activity, cancellation, and no fabricated percentage.
  - Start Indexing navigates to the real background job and preserves truthful completion timing.
evidence_outputs:
  - docs/18-production-evidence/background-import-ux-report.md
---

# UI-006 — Background import experience

## Objective

Replace the blocking generic GitHub-import loading screen with an explicit prepare action and a server-owned staged acquisition experience, while preserving the existing preview/confirm/index contracts.

## Scope

- Add an asynchronous GitHub acquisition entry point and status read without changing direct service compatibility.
- Expose controlled acquisition stages, safe failures and activity logs.
- Keep the Import page mounted during preparation and show elapsed time rather than fake progress.
- Remove automatic GitHub acquisition after paste and wire explicit cancel/prepare actions.
- Preserve background indexing and show its actual job state.
- Give GitHub, ZIP and folder sources one source-aware preparation flow; folder uploads use bounded batches instead of one unbounded multipart request.
- Keep archive-wide ZIP safety limits fail-closed while skipping an individually oversized source file that cannot be indexed.

## Verification

After the owner observed a blank page and requested automated verification, the frontend build/typecheck, lint and all 55 Vitest tests passed. Focused backend import/security/service and API contract coverage passed 68 tests. Two headless Chromium runs exercised the real `Hoang-Sang/recommend_hotel` URL through Prepare Preview and Start Indexing: 63 files were acquired, 34 were indexed, 29 were truthfully skipped, the index completed in 0.7 seconds, cleanup returned 200, and the final run had no console/page errors. The import page now exposes the single implemented indexing pipeline, removes inactive profile controls, uses source-aware four-step preparation for GitHub/ZIP/folder, filters common generated folders locally and uploads browser folders in bounded 200-file batches under a server-owned session. ZIP archives retain path, entry-count, expanded-size and compression-ratio gates, but a truthfully declared oversized source file is now skipped rather than rejecting an otherwise indexable archive; a streamed-size mismatch still fails closed. The owner retained visual UX acceptance. The full backend suite has 288 passes and 31 skips; its 18 failures are the pre-existing frozen evaluation fixture CRLF/checksum mismatch, so this task remains `in_progress` rather than claiming a clean mandatory full gate.

## Rollback

The project owner confirmed on 2026-07-17 that the unrelated frozen-fixture issue
had been handled and explicitly authorized this documentation-only closure. During
AGT-007 verification the main Windows checkout still materialized that tracked LF
fixture as CRLF, while a hash-verified canonical-LF clone passed all 373 backend
tests. The UI-006 implementation and focused evidence above are unchanged.

Restore the synchronous route call and automatic-preview hook behavior, remove the status endpoint/query, and retain the underlying SEC-001/BUG-001 acquisition controls.
