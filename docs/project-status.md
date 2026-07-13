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
| Active task | None; `DAT-001` completed on 2026-07-13 after the foundation tasks |
| Next task candidate | Prepare and authorize `DAT-002` for Alembic setup and the baseline production migration |
| Production readiness | Not ready |

## Verified strengths

- Local FastAPI and React/Vite workspace with import, indexing, exploration, search, evidence, graph, impact, and assistant surfaces.
- Safe archive controls, multi-language parsing, deep Python analysis foundations, deterministic retrieval, evidence IDs, stale evidence, incremental indexing, and grounded fallback.
- Accepted target architecture, domain contracts, production foundation ADR, and a dependency-aware task register.
- Accepted implementation-ready PostgreSQL schema/ERD covering 35 production tables, composite ownership, lifecycle constraints, access indexes, and migration order.

## Blocking gaps

1. Production schema design is established, but Alembic migration history, supported upgrade, and schema-drift evidence are not.
2. Index jobs are process-local rather than durable and recoverable.
3. Index artifacts are not yet published through a validated immutable version boundary.
4. Parser/code-analysis responsibilities overlap and equivalence is not proven.
5. Retrieval, citation, graph, incremental, security, performance, and resilience gates lack complete release evidence.
6. Frontend navigation, server state, error states, accessibility, and E2E coverage are incomplete.
7. Authentication, observability, backup/restore, deployment, and runbooks are not production complete.

The detailed and source-verified account is maintained in `14-implementation-baseline/`. Do not update this page from assumptions.

## Immediate sequence

1. Review the completed `DAT-001` schema design and review evidence.
2. Prepare `DAT-002` with exact Alembic revisions, supported-upgrade fixture, forward-recovery policy, constraint checks, and schema-drift gates.
3. Do not add migrations, repositories, or production database behavior until `DAT-002` is explicitly `ready` or `in_progress`.

## Status update rule

Change this document only when the linked baseline or evidence changes. A task count, merged branch, or working demo does not by itself advance a release level.
