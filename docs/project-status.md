# Project Status

Status: Accepted project control document  
Owner: Project maintainer  
Last verified: 2026-07-17

This page is the operational front door. It reports verified progress; it does not replace product contracts, architecture, tasks, or release evidence.

## Current position

| Item | State |
| --- | --- |
| Target | Release L3: single-node self-hosted production |
| Current maturity | L1 capabilities exist, but the L1 evidence set is incomplete |
| Active delivery phase | Phase 7 has verified SEC-001 and SEC-002; operations delivery remains open |
| Active task | AGT-007 completed locally; Phase 6 task metadata still lists ARCH-001, UI-011 and UI-020 in progress and requires owner reconciliation |
| Next task candidate | Promote RET-004 for a real Ollama sparse/dense/hybrid benchmark, or continue the operations sequence |
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
- Optional provider calls now receive exact whole selected evidence spans rather than citation metadata alone. Current owner/index/source/hash/range/blocked/budget checks fail closed, imported source is delimited as untrusted data, and provider failure preserves deterministic fallback. The AGT-004 provider-context matrix and canonical-LF full backend gate pass; real-provider quality remains unverified.
- Assistant requests now optionally include visible removable workspace context. Code Explorer sends the current file, selected line and containing parsed symbol; Overview sends page-only context. The backend verifies current repository ownership, source hash, line bounds and symbol membership before retrieval anchoring, returns stable 422 context errors before retrieval, and preserves context-free behavior. AGT-005 passes 81 focused backend/API regressions, 113 frontend tests and a 347-pass canonical-LF full backend gate.
- Assistant conversations now expose repository-owned bounded history/replay, retain the server-issued identity across follow-ups, and restore deep-linked transcripts after refresh. A deterministic eight-message/1,000-token projection helps resolve follow-up intent without becoming evidence; stale assistant text is excluded and current-index citation gates remain authoritative. AGT-006 passes 61 focused backend/API regressions, 114 frontend tests and a 354-pass canonical-LF full backend gate.
- Optional chat now has a dependency-free native Ollama adapter restricted to a validated loopback HTTP origin, installed model identity, bounded timeout and response size. Readiness never pulls or mutates models; non-streaming JSON receives only validated AGT-004 evidence context, and outage/malformed/invalid-citation cases preserve deterministic fallback. AGT-007 passes 36 focused tests, 151 combined regressions and a 373-pass canonical-LF full backend gate; live-model quality remains unverified.
- Retrieval evaluation now validates a content-addressed six-case synthetic dataset and compares exact/keyword, deterministic semantic-fixture and hybrid methods on identical inputs with reviewed formulas, negative/ambiguous coverage and reproducible checksums. The EVA-001 clean targeted, compatibility and full local-profile gates pass; real provider quality, accepted thresholds and load evidence remain open.
- A named EVA-002 CI job now combines existing graph/readiness, incremental/equivalence, assistant and evaluation suites with a content-addressed fail-closed smoke policy. Its local clean gate and GitHub-hosted named checks pass; the policy remains explicitly non-release.
- React Router now owns the accepted canonical management/workspace URLs, browser history and reloadable repository/source/line/evidence identity. Missing, unusable, malformed and unsafe contexts fail closed into recovery; the UI-001 targeted/full/lint/typecheck/clean-build and HTTP deep-link gates pass.
- TanStack Query now owns current frontend repository/workspace reads, mutation results, import previews and scoped chat transcripts. Repository/index-version keys, cancellation, bounded classified retry, terminal/hidden polling, scoped invalidation, cached refresh retention and explicit recovery states pass the UI-002 targeted/full/lint/typecheck/clean-build gates.
- Graph GET views now enforce deterministic server-side filters, depth and 220-node/520-edge maxima, disclose counts/coverage/truncation/unresolved roots/provenance, and reject stale compatibility versions. The UI renders the complete returned projection with limited-state, bounded expansion and accessible relation-list alternatives; UI-003 clean backend/frontend gates pass.
- UI-004 renders the complete bounded projection as a connected architecture-layer Graph Explorer with focus, zoom, minimap and contextual support/impact inspection. Overview supplies deterministic signal-backed reading tours, and Impact separates direct, inferred and unknown while declaring historical comparison unavailable. In addition to 45 Vitest tests, six deterministic Chromium tests pass locally with axe serious/critical = 0, reduced-motion coverage and complete 12/80/220-node observations; the named GitHub Actions gate passes.
- SEC-001 now applies one normalized path/tree quota boundary to ZIP, folder and public-Git acquisition; rejects link/special/collision/quota cases; hardens Git URL/ref/configuration/redirect/prompt/hook/submodule/LFS behavior; validates cloned trees; and cleans failed staging. Its 49-test focused gate and full backend regression with 294 passed and 29 integration-profile skips pass without network access.
- SEC-002 now replaces production shared-token compatibility with one-time operator bootstrap, scrypt password verification, strict browser sessions, named Bearer tokens, repository-owner denial, privacy-safe append-only audit and trusted-host recovery. Its focused, full backend, PostgreSQL migration/integration and schema-drift gates pass.

## Blocking gaps

1. The production worker is not yet composed over the typed phase/checkpoint/activation boundary.
2. The incremental planner, intelligence artifacts and readiness calculator are verified independently, but production pipeline/manifest composition and real parser/resolver/graph/readiness equivalence are not proven.
3. Cross-file symbol/inheritance/dynamic resolution, CFG/DFG/non-Python candidates and global canonical graph composition are not proven.
4. The deterministic retrieval evaluation dataset/runner exists, but real provider, answer/citation, graph, security, performance, resilience and load thresholds lack accepted release evidence.
5. UI-004 and UI-005 are verified. Evaluation/Settings placeholders are replaced with safe server-backed reads and explicit unavailable states. Public evaluation runs, settings mutations, historical diff, canonical opaque-version graph POST APIs and accepted performance budgets remain open boundaries.
6. Frontend login UX, rate limiting, automated audit retention, observability, backup/restore and deployment/TLS are not production complete.
The detailed and source-verified account is maintained in `14-implementation-baseline/`. Do not update this page from assumptions.

## Immediate sequence

1. Reconcile the remaining Phase 6 `in_progress` task metadata before selecting unrelated implementation work.
2. Authorize RET-004 only when a real Ollama sparse/dense/hybrid benchmark is desired; keep RET-005 and UI-024 draft until their predecessor evidence exists.

## Status update rule

Change this document only when the linked baseline or evidence changes. A task count, merged branch, or working demo does not by itself advance a release level.
