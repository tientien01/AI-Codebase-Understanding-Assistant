# Detailed Production Storage Design

Status: Accepted production v1 specification  
Authority: Source snapshot, artifact, staging, retention, deletion, and restore behavior  
Owner: Data and operations owners  
Dependencies: `../identity-and-artifact-contract.md`, `detailed-data-model.md`, `../../02-system-architecture/deployment-and-capacity.md`  
Related source: `../../14-implementation-baseline/source-map.md`  
Related tests: path safety, artifact checksum, activation, cleanup, capacity, backup, and restore suites  
Last verified: 2026-07-12

## Storage roles

- PostgreSQL is authoritative for transactional/queryable records and activation.
- Artifact storage holds immutable manifests and large stage/search/graph outputs.
- Repository-owned source storage holds immutable snapshots used by an index.
- Redis holds delivery/coordination only.
- Vector, lexical and graph exports are replaceable derived structures.

A backed-up filesystem adapter is the initial single-node L3 choice when atomic finalize, checksum, quotas, retention, monitoring, and restore evidence pass. An S3-compatible adapter is optional and uses the same opaque-key contract.

## Logical keys

```text
imports/<session-id>/...
repositories/<repository-id>/sources/<snapshot-id>/...
repositories/<repository-id>/indexes/<index-version-id>/manifest.json
repositories/<repository-id>/indexes/<index-version-id>/artifacts/<type>/<key>
evaluation/<run-id>/...
```

These are storage-port keys, not public URLs or host paths. Database rows store opaque keys, schema version, SHA-256, bytes, record count, producer/version, retention class and timestamps.

## Import and source snapshot

Import staging is isolated, quota-bound and expires. ZIP extraction validates canonical paths before writing, rejects absolute/traversal/duplicate-normalized/case-or-Unicode-collision entries, links, special files, nested archives outside policy, excessive entries/bytes/depth/ratio, and disk-reserve violations. Extraction streams with counted compressed/expanded bytes and stops before exhausting the node.

Folder uploads validate each supplied relative path and duplicate. Public Git acquisition uses an isolated destination, bounded shallow fetch, disabled hooks/submodules/LFS, URL/destination checks and process/network/resource limits.

Confirmation creates an immutable snapshot fingerprint from the canonical inventory and bytes. Preview inventory/hashes may be reused only when session, bytes, policy/config version, expiry and snapshot fingerprint match. Indexing never reads a mutable original folder as citation authority.

## Artifact lifecycle

Writers create a version/type-scoped temporary key, stream bytes while hashing/counting, verify schema/checksum/size, then atomically finalize where supported. The immutable manifest is finalized after mandatory artifacts and validation; corrections create a new version.

Readers verify manifest compatibility and checksum before use. Corruption marks dependent capability failed/unavailable, quarantines the artifact when safe, blocks activation, and never falls back to an unrelated version silently.

Artifacts include the canonical scan, parser/resolution outputs needed for reproducibility, graph normalization/validation, fingerprints, chunk/lexical manifests, optional semantic index metadata, and capability/coverage summaries. Whole-graph JSON is an export/diagnostic artifact, never query authority.

## Capacity and duplication

The canonical scan hashes each file once per snapshot. Later stages reuse declared inventory/hash artifacts and parser cache keyed by file hash plus parser/schema/rule versions. Database rows store queryable facts; artifact payloads store replay/diagnostic bulk data. A second complete copy is allowed only for an explicit recovery/export consumer and retention owner.

Capacity evidence measures source and indexable bytes, files, symbols, edges, chunks, embeddings, artifact/database growth, failed/debug amplification, concurrent repositories/jobs and backup size. Hard limits and disk-reserve alarms are explicit deployment configuration established by benchmarks.

## Retention and deletion

Retention classes are active-required, retained-previous/evidence, evaluation/audit, failed-build diagnostic, and temporary/debug. Each has an owner, duration/trigger, reference check and deletion evidence. Provider prompts/responses are not required artifacts and use stricter redaction/retention.

Repository deletion is authorized and tombstoned first. Cleanup enumerates only repository-owned manifest keys, validates every resolved filesystem path remains under the configured root, deletes idempotently, records partial failure, and retries safely. It never deletes an external source path.

## Backup and restore

Backup captures PostgreSQL and all artifacts required by active/retained versions at a recorded consistency boundary. Restore validates schema, ownership, manifest/checksums, source/evidence references and active pointers before readiness. Redis, caches and derived indexes may be rebuilt; they are never restore authority. Restore and forward-recovery/rollback drills are mandatory L3 evidence.

If the restored database references a missing or corrupt mandatory artifact, the service remains unready and must not serve that index. Recovery order is unique:

1. Restore the matching artifact set identified by the backup manifest and verify checksums.
2. If unavailable, atomically select a retained older version only when all of its database records, source snapshot, manifest and mandatory artifacts validate; record a recovery activation audit event.
3. If no retained version validates but an immutable source snapshot exists, keep the repository unavailable and submit a new rebuild after the restore is administratively accepted. The rebuild creates a new index version.
4. If neither a valid retained version nor source snapshot exists, mark the repository `recovery_blocked` and require operator escalation; never synthesize artifacts or clear the active pointer to claim success.

The backup manifest records database backup identity, schema revision, consistency timestamp/LSN where supported, repository active/retained version IDs, required artifact keys/checksums, source snapshot IDs/checksums, configuration profile and release digest. `OPS-003` owns exact commands, RPO/RTO acceptance and exercised restore evidence.
