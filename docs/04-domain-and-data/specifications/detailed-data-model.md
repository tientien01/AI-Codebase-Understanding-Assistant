# Detailed Production Data Model

Status: Accepted production v1 specification  
Authority: Entity semantics, lifecycle, relationships, and required invariants  
Owner: Data owner  
Dependencies: `../identity-and-artifact-contract.md`, `../physical-schema-blueprint.md`, `../../13-decisions/ADR-0001-production-foundations.md`  
Related source: `../../14-implementation-baseline/source-map.md`  
Related tests: migration, constraint, repository-boundary, activation, retention, and restore suites  
Last verified: 2026-07-12

PostgreSQL is the production authority. This document owns logical semantics; migrations own physical names/types and may not weaken the invariants below. Large stage payloads belong in immutable artifacts, not overloaded JSON columns.

## Identity and scoping

Use opaque prefixed database IDs, stable repository-local canonical keys, and immutable versioned observation IDs as separate concepts. Integer `version_number` is display/order metadata and never a globally unique identity. Every repository-scoped row carries the explicit ownership boundary; every derived observation carries `repository_id` and opaque `index_version_id`.

Canonical formats, change behavior, provenance envelope, manifest schema, checksums, and activation preconditions are owned by `../identity-and-artifact-contract.md`.

## Aggregates and tables

| Aggregate | Required records | Key semantics |
| --- | --- | --- |
| Access boundary | principals/sessions or accepted operator identity, repository ownership, audit events | Single-operator L3 is authenticated and authorized; multi-user sharing is deferred |
| Repository | `repositories`, `repository_sources` | Stable identity and source metadata; no job/index/freshness/capability state collapse |
| Import | `import_sessions`, preview/snapshot artifact references | Temporary isolated state, expiry, quotas, warnings, duplicate candidates, idempotent confirmation |
| Jobs | `index_jobs`, `job_attempts` | Request state, attempts, leases, heartbeat, retry, cancellation, progress, terminal reason |
| Index | `index_versions`, `index_artifacts`, `validation_issues`, `capability_readiness` | Immutable build identity, lifecycle, activation, required artifacts, coverage and diagnostics |
| Code intelligence | `files`, `symbols`, `endpoints`, `references`, `chunks` | Versioned canonical observations with source spans, hashes, producer and support |
| Graph | optional `graph_candidates`, canonical `graph_nodes`, `graph_edges` | Candidate audit where retained; canonical directed edges with provenance and same-version FKs |
| Evidence | `evidence`, `citations`, `claims` | Validated support, answer reference, and claim-support mapping remain distinct |
| Assistant | `conversations`, `messages`, `agent_traces`, trace events | User-visible content plus privacy-safe structured decisions/tools/budgets, never hidden reasoning |
| Evaluation | datasets, cases, runs, results | Versioned ground truth, frozen run identity, per-case outputs and aggregates |

## Independent state models

### Repository lifecycle

`active`, `deleting`, `deleted` plus explicit source availability; creation/import progress belongs to `ImportSession`, not `Repository.status`.

### Import session

`created → acquiring → scanning → preview_ready → confirming → confirmed`, with terminal `cancelled`, `expired`, or `failed`. Confirmation is idempotent and publishes a source snapshot or compensates all created state.

### Job and attempt

Job request: `queued → running → succeeded|succeeded_with_warnings|failed|cancelled`. Delivery retries create/advance attempts; lease ownership and heartbeat are attempt fields. `stale` is not a job terminal state.

Each successful claim atomically increments `lease_generation` and creates or selects one `attempt_id`. Every heartbeat, checkpoint, stage write, terminal transition, and activation request includes `(job_id, attempt_id, lease_generation)` and succeeds only when the job is still `running`, the attempt owns the current generation, cancellation is not effective for that boundary, and the lease has not expired. A failed conditional write is `LEASE_LOST`; the worker stops and cannot publish. The generation is the fencing token—worker identity or timestamps alone are insufficient.

### Index version

`building → validating → ready|ready_with_warnings → active → superseded → expired`, with terminal `failed` or `cancelled` before activation. Only one active version exists per repository. Build warning status is not capability readiness.

### Source freshness

`fresh`, `possibly_stale`, `stale`, `source_missing`, `unverifiable`, computed from snapshot/source revision signals and kept separate from lifecycle.

### Capability readiness

Only `ready`, `limited`, `unavailable`, `failed`, or `stale`. Coverage, warning diagnostics, required artifacts, validation reference and remediation are separate fields. `building`, `not_started`, `in_development`, and `ready_with_warnings` are not capability values.

## Required invariants

- One active index version per repository; activation verifies the expected previous version under a repository lock.
- At most one incompatible claimed/running build per repository.
- Unique idempotency key within operation/owner scope.
- Unique `(repository_id, version_number)` and canonical entity key within repository/index/type.
- Files use normalized relative POSIX paths and never persist host absolute paths as product identifiers.
- References and graph edges bind source/target observations in the same repository/index; critical dangling edges cannot be served.
- Inverse graph relations are derived by indexed reverse queries, not stored as duplicate authority.
- Evidence binds repository/index/source key, valid range or file-level location, content hash, support type and provenance. Citation binds a claim/answer to evidence.
- LLM/heuristic facts cannot receive exact/static support types.
- Active or retained evidence/artifacts cannot be deleted by version cleanup.
- Repository deletion is bounded, authorized, audited and idempotent; it never follows untrusted paths.

## Transaction boundaries

1. Import confirmation creates repository/source/snapshot ownership and enqueues the first job atomically or compensates storage.
2. Claim/heartbeat/cancel/retry use conditional writes so a stolen/expired lease cannot commit transitions.
3. Stage writes are bounded batches to an inactive version; large all-at-once transactions are prohibited.
4. Activation verifies manifest/checksums/validation/readiness and switches the active pointer in one transaction.
5. Deletion first records intent/tombstone, then performs idempotent relational/artifact cleanup with an audit outcome.

### Repository deletion with active work

Deletion uses **tombstone, cancel, fence, drain, clean** as the only production behavior:

1. In one transaction, authorize the operator, lock the repository, change lifecycle from `active` to `deleting`, reject future import/sync/index submissions, set `cancellation_requested_at` on every non-terminal job, increment the repository operation generation, and enqueue one idempotent deletion operation.
2. Worker checkpoints and activation compare the repository operation generation as well as the lease generation. A worker holding an older generation cannot write or activate.
3. The deletion worker waits until jobs are terminal or their leases expire; it does not force-delete rows/artifacts that an unfenced worker can still reference.
4. Cleanup enumerates repository-owned records and manifest keys, preserves only explicitly retained audit/evidence required by policy, records partial failures, and retries idempotently.
5. The repository becomes `deleted` only after authoritative rows, required ownership references, and managed artifacts satisfy the deletion validator. A partial cleanup remains `deleting` and is operator-visible.

Delete submission is asynchronous and idempotent. Repeating the same request returns the same deletion operation. A different payload under the same idempotency key is a conflict.

### Cancellation and activation point of no return

The publisher locks the repository/job/candidate version and checks lease generation, repository operation generation, cancellation flag, expected previous active version, manifest/checksums, validation and mandatory readiness in the activation transaction. If cancellation is already effective, the transaction does not activate and the job becomes `cancelled` after safe cleanup.

Once the activation transaction commits, activation is the point of no return: a later cancellation request cannot undo it and returns `CANCELLATION_TOO_LATE` with the successful job/version identity. Rollback is a new validated activation or release recovery operation, never mutation of the committed version.

## Query and index requirements

Migrations derive indexes from verified API/worker queries, including ownership/list order, import expiry, job recovery/lease scanning, repository history, active version, canonical entity lookup, path/symbol/endpoint search, forward/reverse graph adjacency by type, evidence/message lookup, and evaluation run/case access. No query-critical filter or join key may exist only inside JSON.

Cursor pagination uses a stable unique ordering. N+1 access is prevented by bounded bulk loaders/projections and query-count tests. Source/chunk content uses range reads and retention policy; full repository or graph aggregates are not stored in one row.

## Retention and restore

Policy declares active/previous/failed-build artifacts, source snapshots, evidence/chat/trace, evaluations, audit, imports and debug payloads separately. Cleanup is observable, resumable and reference-aware. Backup/restore treats database activation state and required artifact manifests as one consistency set; service remains unready until checksums, ownership, schema and active-version references validate.

## Migration acceptance

Alembic tests cover empty install, supported-version upgrade, forward-recovery/rollback policy, constraints/indexes/FKs, schema drift, representative query plans, backup/restore, and application compatibility. `create_all` and manual compatibility patches remain baseline-only and are forbidden on the production path.
