# Project Status

Status: Accepted project control document  
Owner: Project maintainer  
Last verified: 2026-07-14

This page is the operational front door. It reports verified progress; it does not replace product contracts, architecture, tasks, or release evidence.

## Current position

| Item | State |
| --- | --- |
| Target | Release L3: single-node self-hosted production |
| Current maturity | L1 capabilities exist, but the L1 evidence set is incomplete |
| Active delivery phase | Phase 6 production workspace UX has verified UI-001 navigation and UI-002 server-state foundations; UI-003 through UI-005, composition and release qualification remain open |
| Active task | None; `UI-002` server-state ownership work is verified pending review/merge |
| Next task candidate | `UI-003` after UI-002 review/merge and separate owner authorization |
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
- Assistant sufficiency now requires question-specific strong support/source/endpoint/graph coverage, permits only one controlled budgeted repair, validates claims against selected current citation IDs/scope and rejects optional provider output without valid declarations. The AGT-002 positive/refusal/repair/citation matrix passes.
- Completed assistant turns now persist atomically as redacted conversation messages, claims, citations, budget summaries and controlled ordered trace events. Local SQLite replay enforces repository ownership, production mapping targets the accepted PostgreSQL schema, and persistence failure prevents a successful response. The AGT-003 privacy/rollback/replay matrix passes.
- Retrieval evaluation now validates a content-addressed six-case synthetic dataset and compares exact/keyword, deterministic semantic-fixture and hybrid methods on identical inputs with reviewed formulas, negative/ambiguous coverage and reproducible checksums. The EVA-001 clean targeted, compatibility and full local-profile gates pass; real provider quality, accepted thresholds and load evidence remain open.
- A named EVA-002 CI job now combines existing graph/readiness, incremental/equivalence, assistant and evaluation suites with a content-addressed fail-closed smoke policy. Its local clean gate and GitHub-hosted named checks pass; the policy remains explicitly non-release.
- React Router now owns the accepted canonical management/workspace URLs, browser history and reloadable repository/source/line/evidence identity. Missing, unusable, malformed and unsafe contexts fail closed into recovery; the UI-001 targeted/full/lint/typecheck/clean-build and HTTP deep-link gates pass.
- TanStack Query now owns current frontend repository/workspace reads, mutation results, import previews and scoped chat transcripts. Repository/index-version keys, cancellation, bounded classified retry, terminal/hidden polling, scoped invalidation, cached refresh retention and explicit recovery states pass the UI-002 targeted/full/lint/typecheck/clean-build gates.

## Blocking gaps

1. The production worker is not yet composed over the typed phase/checkpoint/activation boundary.
2. The incremental planner, intelligence artifacts and readiness calculator are verified independently, but production pipeline/manifest composition and real parser/resolver/graph/readiness equivalence are not proven.
3. Cross-file symbol/inheritance/dynamic resolution, CFG/DFG/non-Python candidates and global canonical graph composition are not proven.
4. The deterministic retrieval evaluation dataset/runner exists, but real provider, answer/citation, graph, security, performance, resilience and load thresholds lack accepted release evidence.
5. Frontend bounded graph UX, later production surfaces, accessibility and Playwright E2E coverage remain incomplete; UI-001 covers canonical navigation/deep-link recovery and UI-002 covers current server-state ownership and applicable async/error states.
6. Authentication, observability, backup/restore, deployment, and runbooks are not production complete.

The detailed and source-verified account is maintained in `14-implementation-baseline/`. Do not update this page from assumptions.

## Immediate sequence

1. Review and merge `UI-002` server-state ownership and frontend query evidence.
2. Select and authorize `UI-003` separately after UI-002 is merged.

## Status update rule

Change this document only when the linked baseline or evidence changes. A task count, merged branch, or working demo does not by itself advance a release level.
