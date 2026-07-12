# Project Status

Status: Accepted project control document  
Owner: Project maintainer  
Last verified: 2026-07-12

This page is the operational front door. It reports verified progress; it does not replace product contracts, architecture, tasks, or release evidence.

## Current position

| Item | State |
| --- | --- |
| Target | Release L3: single-node self-hosted production |
| Current maturity | L1 capabilities exist, but the L1 evidence set is incomplete |
| Active delivery phase | Phase 0: verified baseline and executable governance |
| Active task | None; `DOC-001..003` completed on 2026-07-12 |
| Next task candidate | Review the draft `FND-002`; approve its Python lock mechanism, Node range, and frontend lint prerequisite before promotion to `ready` |
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

1. Review the Phase 0 verification reports and accepted cross-cutting contracts.
2. Resolve the three promotion blockers recorded in draft `FND-002`.
3. Promote only the reviewed task to `ready`, then execute it without expanding paths/dependencies.
4. Update baseline, evidence, and this page after every completed task.

## Status update rule

Change this document only when the linked baseline or evidence changes. A task count, merged branch, or working demo does not by itself advance a release level.
