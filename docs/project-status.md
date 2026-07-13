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
| Active delivery phase | Phase 5: bounded assistant foundation (incremental delivery; Phase 3 composition and Phase 4 evaluation evidence remain open) |
| Active task | None; `AGT-001` bounded workflow/tool implementation is verified pending review/merge |
| Next task candidate | `AGT-002` sufficiency, repair and citation validation |
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
- Candidate publication now deterministically checks issues, mandatory artifacts and capability readiness, then performs a lease/operation-fenced expected-previous-version activation that atomically persists readiness, supersedes the old version, switches the repository pointer, completes job/attempt state, and appends audit evidence; the IDX-003 PostgreSQL suite passes.
- Incremental planning now classifies fingerprint changes and exact move candidates, validates producer/configuration compatibility, expands typed reverse dependencies within explicit budgets, and falls back to full with stable reason codes. An exact, bounded canonical-family comparator provides the synthetic equivalence gate required by IDX-004.
- Python parsing now crosses one immutable parse-request and `parsed-file/v1` adapter/IR boundary before an explicit current-state compatibility projection. The duplicate legacy Python AST extractor has been removed, and the INT-001 golden/regression suites pass.
- Python imports and calls now produce deterministic `resolved-reference-set/v1` artifacts retaining resolved, ambiguous and unresolved outcomes with canonical ownership/provenance. Compatibility graph emission consumes those typed outcomes, and the INT-002 resolution matrix passes.
- Resolved Python reference edges now produce provenance-bearing `graph-candidate/v1` records, deterministic accepted/changed/dropped normalization audit and stable issues. Only zero-critical active candidates reach resolved compatibility edges; the INT-003 valid/invalid matrices pass.
- Capability readiness now deterministically maps declared artifact/profile/coverage/reference/validation/freshness/provider/dependency evidence into the accepted five states and manifest-compatible summaries. Mandatory activation permits only ready/limited, and the INT-004 invariant matrix passes.
- Retrieval now uses an owned immutable request/candidate contract, deterministic typed query classifier, and exact/lexical/symbol/endpoint/metadata/graph/semantic adapters while preserving the current search/assistant compatibility projection. The RET-001 positive and insufficient-evidence regression matrix passes.
- Retrieval candidates now pass through a content-addressed immutable configuration, pre-fusion ownership/support/limit filters, owned source-span deduplication and deterministic weighted RRF with bounded score projection. The RET-002 formula, ordering, invariance and negative regression matrix passes.
- Ranked support is now revalidated against current owner/index/source/hash/range/blocked/support policy, selected deterministically as diverse whole spans under a recorded token budget, and persisted with content-bound idempotent evidence identities. The RET-003 positive, rejection, budget and insufficient-evidence matrix passes.
- Assistant routing now uses immutable versioned workflow/tool contracts and an explicit exact/hybrid allowlist. Exact hits avoid hybrid/semantic work, exact misses fall back once, multi-step types route directly to hybrid, and call/time/context/cancellation/deduplication boundaries emit safe observations. The AGT-001 routing/tool matrix passes.

## Blocking gaps

1. The production worker is not yet composed over the typed phase/checkpoint/activation boundary.
2. The incremental planner, intelligence artifacts and readiness calculator are verified independently, but production pipeline/manifest composition and real parser/resolver/graph/readiness equivalence are not proven.
3. Cross-file symbol/inheritance/dynamic resolution, CFG/DFG/non-Python candidates and global canonical graph composition are not proven.
4. Retrieval/evidence evaluation datasets and accepted quality, citation, graph, security, performance, resilience and load thresholds lack complete release evidence.
5. Frontend navigation, server state, error states, accessibility, and E2E coverage are incomplete.
6. Authentication, observability, backup/restore, deployment, and runbooks are not production complete.

The detailed and source-verified account is maintained in `14-implementation-baseline/`. Do not update this page from assumptions.

## Immediate sequence

1. Review and merge the `AGT-001` routing/tool evidence.
2. Authorize `AGT-002` sufficiency, repair and citation validation work.

## Status update rule

Change this document only when the linked baseline or evidence changes. A task count, merged branch, or working demo does not by itself advance a release level.
