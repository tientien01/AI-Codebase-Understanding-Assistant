# Project Status

Status: Accepted project control document  
Owner: Project maintainer  
Last verified: 2026-07-13

This page is the operational front door. It reports verified progress; it does not replace product contracts, architecture, tasks, or release evidence.

## Current position

| Item | State |
| --- | --- |
| Target | Release L3: single-node self-hosted production |
| Current maturity | L1 capabilities exist, but the L1 evidence set is incomplete |
| Active delivery phase | Phase 1: production foundation |
| Active task | None; `FND-002` and `FND-005` completed on 2026-07-13 |
| Next task candidate | Prepare and authorize a scoped `FND-003` task for API contract-preserving route/schema separation |
| Production readiness | Not ready |

## Verified strengths

- Local FastAPI and React/Vite workspace with import, indexing, exploration, search, evidence, graph, impact, and assistant surfaces.
- Safe archive controls, multi-language parsing, deep Python analysis foundations, deterministic retrieval, evidence IDs, stale evidence, incremental indexing, and grounded fallback.
- Accepted target architecture, domain contracts, production foundation ADR, and a dependency-aware task register.

## Blocking gaps

1. Production schema and migration path are not established.
2. Index jobs are process-local rather than durable and recoverable.
3. Index artifacts are not yet published through a validated immutable version boundary.
4. Parser/code-analysis responsibilities overlap and equivalence is not proven.
5. Retrieval, citation, graph, incremental, security, performance, and resilience gates lack complete release evidence.
6. Frontend navigation, server state, error states, accessibility, and E2E coverage are incomplete.
7. Authentication, observability, backup/restore, deployment, and runbooks are not production complete.

The detailed and source-verified account is maintained in `14-implementation-baseline/`. Do not update this page from assumptions.

## Immediate sequence

1. Review the completed `FND-002` install and immutable CI evidence.
2. Prepare a scoped `FND-003` task with exact API-regression gates and allowed paths.
3. Do not change source for `FND-003` until that task is explicitly promoted to `ready` or `in_progress`.

## Status update rule

Change this document only when the linked baseline or evidence changes. A task count, merged branch, or working demo does not by itself advance a release level.
