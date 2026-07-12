# PostgreSQL Physical Schema Blueprint

This blueprint refines entity semantics in `specifications/detailed-data-model.md`. Exact SQL types and names are finalized in migrations, but migrations may not weaken these invariants.

## Repository lifecycle tables

### repositories

Stable repository identity, display name, status summary, active index version ID, timestamps, ownership boundary, deletion state. Do not store large graph/chunk collections in one JSON field.

Indexes: ownership/list ordering, status, source fingerprint. Constraint: active version belongs to the same repository and is publishable.

### repository_sources

Source type, canonical locator, branch/revision metadata, safe credential reference, last synchronized revision, source fingerprint. Unique canonical source within an ownership boundary where duplication policy requires it.

### import_sessions

Temporary source location/reference, state, expiry, preview artifact, limits/warnings, duplicate candidates, confirmed repository, timestamps. State transition and expiry indexes support cleanup.

## Durable indexing tables

### index_jobs

Repository, requested mode, status, attempt, priority, idempotency key, target/base versions, lease owner/expiry, heartbeat, cancellation flag, progress/stage, error code, timestamps.

Constraints prevent incompatible concurrent active jobs. Indexes support queue recovery, repository history, stale lease scanning, and status polling.

### index_versions

Repository, monotonic version number, build/validation/activation status, base version, source revision/fingerprint, artifact schema version, producer version, readiness summary, timestamps. Unique `(repository_id, version_number)` and at most one active version per repository.

### index_artifacts

Version, artifact type, URI/key, schema version, checksum, byte size, content count, producer stage, retention class, creation time. Unique artifact type/key within a version as defined by its contract.

### validation_issues and capability_readiness

Version-scoped issue code/severity/entity/source/details and per-capability state/reasons/required artifacts. Critical issues block activation.

## Code intelligence tables

Files, symbols, endpoints, references, chunks, graph nodes, and graph edges are repository/version scoped. Canonical keys are unique within entity type and version. File-relative paths are normalized and case policy is explicit.

Graph edges reference nodes in the same version and preserve origin, extractor, source location, confidence, support level, and metadata. Chunks preserve source range/hash/type and retrieval metadata; embeddings are replaceable derived indexes.

## Evidence and assistant tables

Evidence stores repository/version/source identity, range, support type, content hash/snapshot policy, retrieval source, freshness, and creation context. Conversations/messages store user-visible content and status. Agent traces store structured workflow/tool/evidence/budget/timing records, never hidden chain-of-thought or secrets.

## Evaluation tables

Datasets/questions/ground truth are versioned. Runs bind method, configuration, code/index/model versions and timestamps. Results preserve retrieved evidence, answer, citations, trace summary, automatic metrics, and manual scores.

## Transaction boundaries

- Confirm import creates repository/source and publishes source atomically or compensates storage.
- Job claim/heartbeat/update uses conditional writes to prevent stolen leases.
- Index activation switches one active pointer and stales affected evidence in one transaction.
- Repository deletion first marks intent, then performs idempotent relational/artifact cleanup with audit outcome.

## Migration and retention

Alembic owns schema history. Large artifact rows are avoided. Retention preserves the active and configured previous versions, evaluation evidence, and audit requirements. Cleanup never deletes artifacts referenced by an active version or retained evidence without policy approval.
