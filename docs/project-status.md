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
| Active delivery phase | Phase 2: durable and atomic indexing |
| Active task | None; `IDX-002` typed phase/checkpoint evidence complete |
| Next task candidate | `IDX-003` validation and atomic activation |
| Production readiness | Not ready |

## Verified strengths

- Local FastAPI and React/Vite workspace with import, indexing, exploration, search, evidence, graph, impact, and assistant surfaces.
- Safe archive controls, multi-language parsing, deep Python analysis foundations, deterministic retrieval, evidence IDs, stale evidence, incremental indexing, and grounded fallback.
- Accepted target architecture, domain contracts, production foundation ADR, and a dependency-aware task register.
- Accepted implementation-ready PostgreSQL schema/ERD covering 35 production tables, composite ownership, lifecycle constraints, access indexes, and migration order.
- Alembic production baseline, PostgreSQL 18.4 integration profile, zero-drift gate, and supported nine-table SQLite upgrade mapper verified by `DAT-002`.
- Explicit production PostgreSQL profile, Alembic-head startup guard, typed repository port, and PostgreSQL repository/evidence adapter verified by `DAT-003`; SQLite remains the local default.
- Dramatiq 2.2.0 selected by `ADR-0003` after passing 15/15 Redis recovery/cancellation PoC runs.
- Production background dispatch now persists queued PostgreSQL jobs, publishes one-ID Dramatiq messages, and runs through a dedicated worker boundary; duplicate, broker-outage, and worker-restart tests pass under `JOB-003`.
- Production job delivery now uses PostgreSQL attempt leases, generation fencing, heartbeat, durable cancellation, bounded retry, and stale-worker recovery; the JOB-004 resilience suite passes.
- Index artifacts now have a typed `index-manifest/v1`, safe repository/version-owned logical keys, checksum-verified immutable filesystem storage, and deterministic terminal publication; the IDX-001 suite passes.
- Indexing now has strict production-v1 phase contracts, deterministic idempotency identities, classified failures, cancellation boundaries, immutable checkpoint envelopes, and prefix-only checksum-validated resume planning; the IDX-002 suite passes.

## Blocking gaps

1. Validation, production worker composition, and atomic activation are not yet implemented over the typed phase boundary.
2. Parser/code-analysis responsibilities overlap and equivalence is not proven.
3. Retrieval, citation, graph, incremental, security, performance, and resilience gates lack complete release evidence.
4. Frontend navigation, server state, error states, accessibility, and E2E coverage are incomplete.
5. Authentication, observability, backup/restore, deployment, and runbooks are not production complete.

The detailed and source-verified account is maintained in `14-implementation-baseline/`. Do not update this page from assumptions.

## Immediate sequence

1. Publish and review the `IDX-002` phase/checkpoint evidence.
2. Authorize `IDX-003` before implementing validation and atomic activation.

## Status update rule

Change this document only when the linked baseline or evidence changes. A task count, merged branch, or working demo does not by itself advance a release level.
