# IDX-003 Validation and Atomic Activation Evidence

Status: Passed

Verified: 2026-07-13

Task: `IDX-003`

## Delivered boundary

- Added strict validation issue and capability-readiness contracts with deterministic mandatory/optional behavior.
- Added consistency checks across manifest summaries, readiness records, mandatory artifact declarations, validation issues, and immutable artifact metadata.
- Added immutable manifest publication before database activation.
- Added one PostgreSQL activation transaction that locks and fences repository, job, attempt, candidate, and expected previous version state.
- The transaction persists validation/readiness, supersedes the expected old version, activates the candidate, switches the repository pointer, completes job/attempt state, and appends one audit event.
- Added idempotent success replay and explicit cancellation-too-late behavior after committed activation.

No database migration, production worker wiring, API, local indexing rewrite, incremental behavior, dependency, or frontend change was made.

## Verification profile

- Project virtual environment: `backend/.venv`
- PostgreSQL: pinned `postgres:18.4-bookworm` integration service on `127.0.0.1:55432`
- Redis: pinned integration service on `127.0.0.1:56379/15`
- Artifact backend: isolated `tmp_path` filesystem roots with synthetic bytes

## Commands and results

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/indexing -q
# 15 passed, 5 PostgreSQL tests skipped in 0.66s

docker compose -f compose.integration.yml up -d postgres redis
# PostgreSQL and Redis started successfully

$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
$env:TEST_REDIS_URL='redis://127.0.0.1:56379/15'
backend\.venv\Scripts\python.exe -m pytest tests/jobs/test_job_state_store.py tests/indexing -q
# 24 passed in 5.22s

backend\.venv\Scripts\python.exe -m pytest tests -q
# 132 passed, 2 known warnings in 74.88s

git diff --check
# Passed with no output

docker compose -f compose.integration.yml down
# Integration services and network removed successfully
```

The warnings are the existing duplicate-ZIP fixture warning and an OpenTelemetry dependency deprecation warning.

## Verified invariants

- Critical validation issues, missing readiness, non-ready mandatory capabilities, undeclared mandatory artifacts, and manifest/readiness mismatch block publication or activation.
- Optional semantic failure remains recorded without blocking a ready deterministic exploration capability.
- Corrupt filesystem bytes or mismatched PostgreSQL artifact metadata preserve the previous active version.
- Cancellation, stale lease generation, stale repository generation, changed expected active pointer, and invalid candidate identity cannot mutate activation state.
- A valid candidate updates every authoritative activation record and produces exactly one append-only audit event.
- Replaying a committed activation is idempotent and a later cancellation request returns too-late.
- An exception injected after all transaction statements rolls back repository pointer, both version lifecycles, job/attempt completion, readiness rows, and audit insertion.

## Remaining work

IDX-004 owns affected-set planning and full/incremental equivalence. Production worker composition over the typed phase/checkpoint/activation boundary remains an explicit gap and Phase 2 is not claimed complete by this report.
