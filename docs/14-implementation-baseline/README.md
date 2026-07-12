# Current Implementation Baseline

This section describes verified source as of 2026-07-12. It is not the production target.

## Verification set

- `verification-report.md`: environment, commands, pass/fail results and Phase 0 blockers.
- `api-coverage.md`: current 43-handler HTTP surface and production-contract gaps.
- `test-inventory.md`: 52-test backend suite, frontend gates and missing suites.
- `capability-baseline.md`: implemented/partial/placeholder/production-blocked capability matrix.
- `source-map.md`: targeted source locations.
- `production-gap-analysis.md`: prioritized migration from this baseline to target.

## Current strengths

- FastAPI + React/Vite local-first workspace with import, indexing, exploration, search, evidence, graph, impact, and assistant surfaces.
- Safe archive controls, multi-language parsing, deep Python IR/CFG/DFG/CPG foundations.
- Deterministic hybrid retrieval, local sparse vectors, evidence IDs, citation validation, stale evidence, incremental indexing, graph projections, and grounded fallback.

## Critical production blockers

- Background indexing uses process-local daemon threads and in-memory control events.
- SQLite `create_all`/compatibility column patches replace proper production migrations.
- Optional shared API token is not a complete public deployment identity/access design.
- No durable worker recovery, atomic version artifact boundary, production queue, or production database profile.
- Evaluation and settings surfaces are partial; conversation/trace persistence is incomplete.
- Observability, deployment, backup/restore, CI gates, frontend tests, performance/resilience/security evidence are incomplete.

## Hotspots

- `backend/app/services/indexing/indexing_service.py`: orchestration, job control, incremental planning, merge, cleanup, fingerprint, debug output, and execution in one service.
- `backend/app/services/codebase_service.py`: broad facade/service locator spanning most domains.
- `backend/app/services/ingestion/import_session_service.py`: upload, preview, duplicate detection, Git clone, fingerprint, confirm, rollback.
- `backend/app/services/repositories/repository_store.py`: large aggregate hydration plus repository/job/evidence persistence.
- `backend/app/api/v1/routes/repositories.py` and `backend/app/schemas/api.py`: many domains concentrated in one route/schema module.
- `frontend/src/hooks/useAppController.ts`: navigation and most feature/server state in one hook.
- `frontend/src/pages/workspace/GraphPage.tsx`: silent small client truncation instead of explicit server projection/coverage.

## Duplication risk

`services/parsing/` and `services/code_analysis/` overlap in language analysis responsibilities. The target contract requires a canonical adapter → IR → resolver → optional CFG/DFG → graph candidate pipeline and explicit compatibility deprecation.

## Simplicity risks

Current in-memory retrieval and heuristic classification are excellent deterministic baselines but require persistent indexes, versioned ranking config, token budgeting, scalable reads, trace persistence, and regression benchmarks before production scale claims.
