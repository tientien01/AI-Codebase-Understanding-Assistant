# IDX-001 Immutable Artifact Manifest and Store Evidence

Status: Passed

Verified: 2026-07-13

Task: `IDX-001`

## Delivered boundary

- Added the typed, strict, deterministic `index-manifest/v1` contract.
- Added repository/index-version-owned logical keys and a filesystem `ArtifactStore` port adapter.
- Added same-directory temporary staging, exact SHA-256 and byte-count verification, atomic no-overwrite finalization, and verified reads.
- Added idempotent identical retries, immutable conflict detection, safe failure messages, and terminal manifest publication after artifact validation.
- Added explicit production `ARTIFACT_ROOT` configuration and composition-root selection.

No indexing pipeline, database schema, activation transaction, cleanup worker, S3 adapter, API, or frontend behavior changed.

## Verification profile

- Project virtual environment: `backend/.venv`
- PostgreSQL: pinned `postgres:18.4-bookworm` integration service on `127.0.0.1:55432`
- Redis: pinned integration service on `127.0.0.1:56379/15`
- Artifact tests: isolated `tmp_path` roots and synthetic bytes only

## Commands and results

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/artifacts -q
# 18 passed in 0.30s

docker compose -f compose.integration.yml up -d postgres redis
# PostgreSQL and Redis started successfully

$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
$env:TEST_REDIS_URL='redis://127.0.0.1:56379/15'
backend\.venv\Scripts\python.exe -m pytest tests/persistence -q
# 13 passed, 1 dependency deprecation warning in 3.55s

backend\.venv\Scripts\python.exe -m pytest tests -q
# 112 passed, 2 known warnings in 55.80s

git diff --check
# Passed with no output

docker compose -f compose.integration.yml down
# Integration services and network removed successfully
```

The two full-suite warnings are the existing duplicate-ZIP fixture warning and an OpenTelemetry dependency deprecation warning. Neither changes the IDX-001 gate result.

## Verified failure cases

- Unsafe, absolute, backslash, traversal, malformed-owner, and reserved keys fail before writing.
- Declared checksum/size mismatches leave neither a finalized object nor a temporary file.
- Duplicate identical writes converge on one object; conflicting writes preserve the original bytes.
- Missing or corrupt objects never return unverified bytes and errors do not disclose the host root.
- Invalid manifest schema, identity, URI, or timestamps fail validation.
- Nonterminal manifests and manifests without a declared validation report cannot publish.

## Remaining work

IDX-001 does not make an index version active. Resumable stage checkpoints remain `IDX-002`; validation and atomic activation remain later authorized tasks.
