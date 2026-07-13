# PostgreSQL Schema Design Review Report

Status: Verified design evidence

Owner: Project maintainer

Verified: 2026-07-13

Task: `DAT-001`

## Scope

This report verifies that the PostgreSQL physical schema and ERD implement the accepted production data semantics closely enough for `DAT-002` to create Alembic migrations without inventing physical boundaries. It is documentation evidence only: no PostgreSQL DDL, migration, application compatibility, query plan, or runtime behavior has been implemented or verified.

## Artifact inventory

| Artifact | Verified content |
| --- | --- |
| `docs/04-domain-and-data/postgresql-physical-schema.md` | 35 tables, shared type/nullability/default conventions, lifecycle checks, keys/FKs, 24 named access-pattern indexes, transactions, and migration order |
| `docs/04-domain-and-data/postgresql-erd.md` | Five aggregate ERDs containing all 35 tables plus a cross-aggregate composite-FK catalog |
| `docs/04-domain-and-data/database-design.md` | Explicit DAT-001 design authority and DAT-002 handoff |

## Contract review

| Accepted invariant | Physical enforcement/design | Result |
| --- | --- | --- |
| Database IDs, canonical keys, versioned observations, and evidence IDs remain distinct | Opaque prefixed PKs plus repository/version-scoped canonical uniqueness | Pass |
| Every derived record binds repository and opaque index version | Composite `(repository_id, index_version_id)` FKs across observations, graph, evidence, claims, citations, traces, and evaluation | Pass |
| One active version per repository | Partial unique index, deferred active-pointer FK, and deferred active-lifecycle constraint trigger | Pass |
| A second incompatible production v1 build is rejected | Partial unique index on queued/running index jobs | Pass |
| Lease loss fences stale workers | Job/attempt/generation fields, unique generation, repository operation generation, and conditional transaction predicate | Pass |
| Import confirmation is idempotent and snapshot-bound | Scoped idempotency uniqueness plus one confirmation transaction creating repository/source/snapshot/job references | Pass |
| Graph edges reference same-version valid nodes | Composite source/target graph-node FKs containing repository and index version | Pass |
| References retain resolved, ambiguous, and unresolved outcomes | Checked outcome with target/candidate presence rules | Pass |
| Evidence has valid version/source/range/hash/support/freshness | Version/file composite FKs, paired inclusive-range checks, checksum, support and freshness checks | Pass |
| Claims, citations, and evidence remain distinct and scope-equal | Separate tables with composite claim/evidence citation FKs | Pass |
| Activation preserves the previous version on failure | Locked expected-previous activation transaction with deferred constraints and one active pointer | Pass |
| Repository deletion is tombstone/cancel/fence/drain/clean | Repository generation, durable deletion operation, active-operation uniqueness, and staged transaction boundary | Pass |
| Query-critical identity/state is not hidden in JSON | Named relational columns for ownership, lifecycle, lease, range, retention, and joins | Pass |
| Indexes derive from accepted consumers | Each of 24 named indexes maps to API, worker, cleanup, activation, graph, conversation, audit, or evaluation access | Pass |
| Secrets and hidden reasoning are not persisted | Token hashes/credential references only; trace payloads are privacy-safe and have no chain-of-thought/prompt-dump field | Pass |
| Alembic can create cyclic ownership safely | Nine ordered migration groups identify base tables, deferred cycles, partial indexes, triggers, and compatibility tests | Pass |

No unresolved P0 schema ambiguity remains for the DAT-002 baseline-migration task. Technology selection for full-text, trigram, vector, queue, and external graph/search indexes remains intentionally deferred.

## Verification commands

| Command | Result |
| --- | --- |
| Heading/table inventory `rg` commands declared by DAT-001 | Pass: 35 physical table headings and all mandatory aggregate names present in schema and ERD |
| `git diff --check` over DAT-001 allowed documentation paths | Pass: no whitespace errors |
| `git diff --name-only -- backend frontend tests storage` | Pass: no runtime, test, fixture, or storage path changed |

## DAT-002 handoff

`DAT-002` must translate this design into Alembic revisions and prove empty install, supported upgrade/data mapping, FK/check/partial-index behavior, forward-recovery policy, schema drift, and application compatibility. This review does not satisfy any of those migration gates.
