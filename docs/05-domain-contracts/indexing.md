# Indexing and Job Contract

## Durable job semantics

- PostgreSQL is the authoritative job state; queue messages carry job IDs.
- Submission is idempotent.
- Workers claim a lease, heartbeat, checkpoint between safe phases, and release or recover stale claims.
- Retries are bounded and distinguish transient from permanent failure.
- Cancellation is durable and cooperative; pause is supported only if its cross-restart semantics are fully implemented.
- Worker shutdown is graceful and does not publish partial state.

## Incremental correctness

The planner classifies added, changed, deleted, and unchanged files by stable fingerprint, derives affected dependents, reuses only compatible artifacts, and validates output. For unchanged areas, full and incremental builds must produce equivalent canonical entities, graph, chunks, and benchmark answers.

## Publish invariant

Build artifacts are immutable. Validation creates explicit issues and readiness. A single transaction switches the active pointer; old evidence is marked stale without deleting historical provenance.
