# Phase 1 — Production Foundation

Status: Approved; blocked by Phase 0 exit

## Outcome

Production data changes are versioned and transactional, while broad API/schema/facade responsibilities begin moving behind domain application boundaries without product behavior drift.

## Tasks

`FND-002` through `FND-004`, `DAT-001` through `DAT-003` in `../task-register.md`. Phase 0 prerequisite `FND-005` must complete before `FND-002` is promoted to `ready`.

## Entry

Phase 0 exits; dependency and schema decisions are accepted; PostgreSQL integration environment is reproducible.

## Exit gates

- Locked dependency/project metadata and CI install are reproducible.
- Fresh and supported-existing databases migrate to Alembic head; schema drift checks pass.
- PostgreSQL is the production profile and SQLite remains a declared local/test profile.
- Repository boundaries and multi-table transactions enforce index/repository ownership.
- Route/schema/facade splits preserve the verified API contract.

## Evidence

Install report, migration upgrade/drift/restore tests, PostgreSQL integration suite, and API contract regression.
