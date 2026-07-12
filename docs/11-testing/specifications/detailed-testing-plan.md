# Detailed Production Testing Plan

Status: Accepted test coverage contract; executable commands are task-owned  
Authority: Required test layers, fixtures, invariants, fault cases, and evidence mapping  
Owner: Test owner  
Dependencies: `../README.md`, `../fixture-catalog.md`, accepted product/domain/API/security/operations contracts  
Related source: `../../14-implementation-baseline/source-map.md`  
Related tests: current inventory in `../../14-implementation-baseline/test-inventory.md`  
Last verified: 2026-07-12

## Execution rule

Each `ready` task declares exact targeted and mandatory commands, environment/profile, fixtures, expected result and evidence destination. This plan does not authorize a generic `pytest` that can collect imported repositories. Test discovery is restricted to project test roots and excludes storage, imports, dependencies, builds and archives.

Automated suites use synthetic secret-free fixtures and deterministic fake providers. Production-provider, performance, deployment and recovery drills run separately with frozen configuration and immutable evidence.

## Test layers

| Layer | Required purpose |
| --- | --- |
| Unit | canonical IDs, state machines, filters, parsers, resolver rules, ranking, evidence/sufficiency, validators |
| Integration | PostgreSQL repositories/transactions, Alembic, queue/worker, artifacts, providers, activation, retention |
| Contract | OpenAPI, error envelope, auth/idempotency/cursor/range/projection, artifact/IR/graph/tool/trace schemas |
| E2E | import → preview → index/recovery → explore/search/assistant/evidence → re-index/stale → delete |
| Security | archive/Git/parser/provider/prompt/secret/auth/rate/quota/deletion/supply-chain boundaries |
| Performance | repository classes, indexing stages, queries, graph projection/layout, frontend large data, storage growth |
| Resilience/operations | API/worker/DB/Redis/artifact/provider/disk restart/fault, migration, backup/restore, rollback |
| Evaluation | exact/keyword/naive-vector/hybrid/reranker/agent comparison and release thresholds |

## Fixture contract

Every fixture declares revision/checksum, expected files/entities/relations/paths/evidence, allowed alternatives, intentionally ambiguous/unresolved cases, security contents, incremental mutations and owning tests. Golden outputs change only through reviewed semantic changes with explanation.

Required families are maintained in `fixture-catalog.md`: reference FastAPI/React flow, parser/resolver cases, structural TypeScript/React, endpoint/framework ambiguity, incremental add/edit/delete/move/rename/signature changes, invalid graph candidates, evidence/security cases, retrieval benchmark, large synthetic projection and unsafe archives.

Add production-critical fixtures for job fencing/delete races, complete language-profile failure, excessive unresolved references, restore manifests with missing/corrupt artifacts, `.env.example` containing seeded secret values, and prompt-injection source.

## Import and security

Verify interrupted upload creates no published session and TTL cleanup removes temporary bytes; confirmation idempotency; expired/changed preview; traversal, normalized/case/Unicode duplicates, links, special/nested files, ZIP ratio/entry/byte/depth/disk limits; public-Git URL/redirect/SSRF/protocol/port/credential/hooks/submodules/LFS/time/size; secret detection before parse/embed/provider/log/evidence/export; and bounded cleanup.

## Jobs, versions and activation

Verify submission idempotency and second incompatible request returns the active job; claim increments lease generation; heartbeat/checkpoint/stage writes use fencing predicates; stale worker cannot write or publish; duplicate delivery has one authoritative effect; valid stage checkpoint resumes and invalid partial stage restarts; bounded retry/backoff; cancel at each stage; cancellation before activation prevents publish; cancellation after commit returns too-late; DB/Redis/artifact/disk/OOM/timeout faults preserve the previous active version.

## Deletion and retention

Race delete against queued/running/stale workers and activation. Assert repository tombstone rejects new work, cancellation and operation generation fence workers, deletion waits for terminal/expired leases, partial cleanup remains `deleting`, retries are idempotent, retained audit/evidence follows policy, and no path outside owned manifests is deleted.

## Parser, resolver and graph

Golden tests cover deterministic repeat output, schema versions, canonical line-shift/move/rename identity, malformed/unsupported syntax, aliases/ambiguity, file-local parser boundary, resolver outcomes, complete language-profile failure, unresolved coverage, graph candidate provenance, deterministic merge, single canonical edge direction, invalid/dangling/duplicate handling and mandatory-capability activation rules.

Every active confirmed graph edge has valid same-version endpoints and provenance. Bounded query tests enforce type/direction/depth/node/edge/result/time limits and verify coverage/truncation/continuation, including accessible frontend list fallback.

## Full and incremental equivalence

For every change class, build the same target snapshot by clean full and incremental paths. Compare canonical facts, resolved/ambiguous/unresolved references, graph, chunks/lexical state, optional compatible semantic state, readiness/coverage and unchanged evaluation cases. Exceeding affected-set/compatibility limits must choose full build and record the reason.

## Retrieval, evidence and assistant

Assert exact target lookup avoids semantic/planner/provider calls; lexical and versioned RRF tie order are deterministic; candidates remain distinct from evidence; evidence enforces principal/repository/index/source/range/hash/secret/support/provenance/freshness; claims map to citations; invalid claims repair once or become insufficient.

Run positive, negative, ambiguous, stale, unsupported-language, incomplete-graph, provider outage, prompt injection, budget/cancellation, large-repository and cross-repository cases. Enforce tool JSON schemas, allowlist, per-tool and workflow budgets, trace redaction and no hidden reasoning/raw secrets.

## API and frontend

Generate/check OpenAPI and frontend types; snapshot breaking changes; test authentication/session/API-token/CSRF/origin, non-disclosing authorization, request IDs, error envelope, idempotency hash behavior, stable cursors, opaque index IDs, async refs, range/projection caps, retry hints and degraded results.

Frontend coverage includes Router deep links, Query cache/version invalidation, all applicable async states, virtualized/paginated trees, range-loaded code, cancelled search, polling backoff/terminal stop, graph coverage/truncation/provenance, evidence/claim display, sanitization, keyboard/focus/live-region/contrast and critical Playwright journeys.

## Migration, deployment and recovery

Alembic tests cover empty install, supported upgrade, constraints/indexes/FKs, drift, PostgreSQL query plans and declared forward-recovery/rollback. Production smoke covers locked non-root images, Compose/TLS/config/startup/readiness and optional-provider degradation.

Backup/restore tests freeze database/artifact/source manifest identity; verify matching restore, missing/corrupt artifact unready state, validated older-version recovery, new rebuild from immutable snapshot, recovery-blocked outcome, Redis/cache rebuild and RPO/RTO measurement. Exact commands and drill evidence are owned by `OPS-003`/release tasks.

## Completion evidence

A task is complete only when targeted and required integration/regression commands pass and their artifacts are stored/linked at the task-declared destination. A release additionally needs API, migration, security, performance, resilience, retrieval/evaluation, frontend accessibility/E2E, deployment and backup/restore evidence for the same immutable candidate.
