---
id: IDX-001
title: Define the immutable artifact manifest and filesystem store
status: completed
priority: P0
phase: 2
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [DAT-003]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/04-domain-and-data/specifications/detailed-storage-design.md
  - docs/05-domain-contracts/indexing.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/environment-and-configuration.md
  - docs/03-technology/stack-overview.md
  - docs/11-testing/specifications/detailed-testing-plan.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/core/config.py
  - backend/app/services/application/container.py
  - backend/app/services/artifacts/**
  - tests/artifacts/**
  - tests/persistence/test_production_repository.py
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/indexing/IDX-001-immutable-artifact-manifest-store.md
  - docs/18-production-evidence/artifact-manifest-store-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/migrations/**
  - backend/app/db/models.py
  - backend/app/db/production_models/**
  - backend/app/api/**
  - backend/app/services/indexing/indexing_service.py
  - backend/app/workers/**
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - The index-manifest/v1 schema validates repository/version ownership, terminal build identity, artifact metadata, capability/coverage objects, validation summary, and timezone-aware timestamps.
  - Artifact keys are opaque relative POSIX keys scoped to one repository/index version and cannot escape or alias the configured root.
  - Filesystem writes hash and count exact bytes in a same-directory temporary file, verify declared metadata, and atomically finalize without overwriting a different existing object.
  - Repeating an identical write is idempotent; conflicting bytes at an existing immutable key fail without mutation.
  - Readers verify SHA-256 and byte size before returning bytes; missing or corrupt objects produce stable safe errors.
  - A terminal manifest finalizes only after every declared artifact and validation report validates, and the manifest bytes are deterministic and immutable.
evidence_outputs:
  - docs/18-production-evidence/artifact-manifest-store-report.md
---

# Task IDX-001 — Define the immutable artifact manifest and filesystem store

## Context

PostgreSQL already has index-version and artifact metadata tables, but runtime code has no `ArtifactStore` port, safe filesystem adapter, or executable `index-manifest/v1` schema. Large stage payloads therefore lack a checksum-verified immutable storage boundary.

## Objective

Add a typed, deterministic manifest model and initial filesystem artifact adapter that can safely stage, finalize, read, and verify repository/version-owned artifacts without changing the indexing pipeline or activation transaction.

## In scope

- Explicit `ARTIFACT_ROOT` configuration with a local/test default and required production override.
- Typed artifact-store port, immutable filesystem adapter, safe logical-key builder, and stable errors.
- Exact SHA-256/byte-count metadata, same-directory temporary staging, atomic finalize, idempotent identical retry, and conflicting-write rejection.
- Typed `index-manifest/v1` model, deterministic canonical JSON, declared-artifact verification, and fixed manifest key publication.
- Unit/path/corruption/concurrency tests plus production-profile configuration regression.

## Out of scope

Pipeline phase refactoring, checkpoint/resume integration, PostgreSQL artifact-row writes, validation issue generation, capability calculation, activation, cleanup/retention workers, S3 implementation, backup/restore drills, HTTP APIs, and frontend work.

## Existing code to reuse

- `Settings` path resolution and production-profile validation.
- PostgreSQL `index_versions`/`index_artifacts` schema and `JobStateStore.register_artifact`; this task does not duplicate or migrate them.
- Python standard-library `hashlib`, temporary files, `os.replace`, and Pydantic already locked by the project.

## Implementation sequence

1. Add and validate `ARTIFACT_ROOT`, resolving local relative paths beneath the project root.
2. Define safe repository/version artifact keys and a storage-port metadata/result contract.
3. Implement streaming filesystem staging, checksum/size verification, atomic immutable finalize, and verified reads.
4. Implement the typed manifest schema and deterministic canonical serialization.
5. Verify every declared artifact/report before publishing a terminal manifest to its fixed key.
6. Add targeted tests and record evidence/baseline updates.

## Data/API compatibility and migration

No database migration or HTTP change is allowed. Existing PostgreSQL artifact columns already match the manifest/store metadata. Local/test profiles gain a resolved filesystem default. Production composition requires an explicit `ARTIFACT_ROOT`; the path value is never exposed through API errors or manifest content.

## Failure, security, performance, and observability requirements

- Reject empty, absolute, backslash, dot-segment, NUL, wrong repository/version, and reserved manifest-as-artifact keys before filesystem access.
- Resolve every operation beneath the configured root and never follow a logical key outside it.
- Stream writes in bounded chunks without requiring a second whole-payload copy; hash/count while writing.
- Temporary names are opaque, same-directory, and removed on validation/finalize failure.
- Stable errors identify the logical key and failure class only; they never include the host artifact root or temporary path.
- Corruption never returns bytes, silently rewrites an object, or falls back to another index version.

## Required tests and commands

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/artifacts -q
docker compose -f compose.integration.yml up -d postgres redis
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
$env:TEST_REDIS_URL='redis://127.0.0.1:56379/15'
backend\.venv\Scripts\python.exe -m pytest tests/persistence -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
docker compose -f compose.integration.yml down
```

The filesystem tests use only `tmp_path` and synthetic secret-free bytes. PostgreSQL/Redis use the disposable integration profile declared by `compose.integration.yml`. Exact results are recorded in `docs/18-production-evidence/artifact-manifest-store-report.md`.

## Acceptance criteria

- Valid manifest data round-trips through deterministic canonical JSON; invalid schema version, ownership, checksum, URI, status, or timestamps fail validation.
- Safe keys resolve under `ARTIFACT_ROOT`; traversal, absolute, backslash, malformed ownership, and manifest-key misuse fail before a write.
- Exact declared bytes finalize with matching SHA-256 and size; mismatched declarations leave no finalized or temporary object.
- Concurrent/duplicate identical finalization yields one immutable object; different bytes for the same key fail and preserve the first object.
- Verified reads reject missing, size-mismatched, or checksum-mismatched objects with no host-path disclosure.
- Manifest publication fails when any declared artifact or validation report is missing/corrupt and succeeds idempotently only at the canonical manifest key.
- Targeted artifact tests, persistence integration, full backend regression, and diff hygiene pass.

## Rollback

Stop producers, remove the filesystem adapter/model/composition selection, and restore the prior configuration. This task has no production pipeline writer and no database migration. Any test artifacts remain isolated under their temporary roots and may be removed by the test harness.

## Documentation and evidence updates

Complete the task only after every command passes. Update source/test baselines and project status, publish the artifact manifest/store report, and advance the next candidate to `IDX-002` without claiming artifact activation or Phase 2 completion.

## Closing evidence

Completed on 2026-07-13. The targeted artifact suite passed 18 tests, the persistence suite passed 13 tests, and the full backend regression passed 112 tests. Exact commands, environment, results, and scope boundaries are recorded in `docs/18-production-evidence/artifact-manifest-store-report.md`.
