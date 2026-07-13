---
id: DAT-002
title: Add Alembic and the baseline PostgreSQL migration
status: completed
priority: P0
phase: 1
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [DAT-001, FND-002]
requirements: []
contracts:
  - docs/04-domain-and-data/postgresql-physical-schema.md
  - docs/04-domain-and-data/postgresql-erd.md
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/04-domain-and-data/specifications/detailed-data-model.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
  - docs/13-decisions/ADR-0002-reproducible-development-toolchain.md
technology_docs:
  - docs/03-technology/stack-overview.md
  - docs/03-technology/environment-and-configuration.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - .github/workflows/ci.yml
  - compose.integration.yml
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - backend/alembic.ini
  - backend/migrations/**
  - backend/app/db/production_base.py
  - backend/app/db/production_models/**
  - backend/app/db/legacy_upgrade.py
  - backend/scripts/migrate_legacy_sqlite.py
  - tests/migrations/**
  - docs/03-technology/stack-overview.md
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/persistence/DAT-002-alembic-baseline-migration.md
  - docs/17-runbooks/development-setup.md
  - docs/18-production-evidence/migration-verification-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/db/models.py
  - backend/app/db/session.py
  - backend/app/services/**
  - backend/app/api/**
  - frontend/**
  - tests/fixtures/**
  - storage/**
dependency_changes:
  allowed: true
  add:
    - psycopg[binary]>=3.3,<4.0
  remove: []
production_gates:
  - A fresh PostgreSQL 18.4 database upgrades to Alembic head with all 35 DAT-001 tables, constraints, partial indexes, deferred ownership, and no create_all path.
  - A synthetic database matching the supported current nine-table SQLite schema maps deterministically into the production schema or fails without a partial target commit.
  - Production SQLAlchemy metadata, Alembic head, and an upgraded PostgreSQL database have zero schema drift.
  - Existing local SQLite runtime behavior and the complete backend suite remain unchanged.
evidence_outputs:
  - docs/18-production-evidence/migration-verification-report.md
---

# Task DAT-002 — Add Alembic and the Baseline PostgreSQL Migration

## Context

`DAT-001` fixes the 35-table production PostgreSQL design, but the repository still initializes nine SQLite tables through `create_all` and manual compatibility patches. Alembic is already locked; no PostgreSQL driver, migration environment, production metadata, integration service, supported-upgrade fixture, or drift gate exists.

## Objective

Create a reproducible Alembic baseline for the DAT-001 schema, prove fresh and supported-legacy upgrades on PostgreSQL 18.4, and add a zero-drift gate without changing the current application persistence path.

## In scope

- Add Psycopg 3 binary as the SQLAlchemy/Alembic PostgreSQL driver and refresh the hashed Python lock.
- Add a test-only PostgreSQL 18.4 Compose service and matching GitHub Actions service pinned to `postgres:18.4-bookworm@sha256:d9c83446333daec3f0588cc709adb80c26090b7f9f0f7ec8d43c243385d79818`.
- Add a separate `ProductionBase` and production model modules for all 35 DAT-001 tables; do not attach them to the current SQLite `Base`.
- Configure Alembic to read `DATABASE_URL`/test override through the backend configuration boundary without embedding credentials.
- Create ordered baseline revisions matching the nine DAT-001 migration groups, including deferred cyclic FKs, partial unique indexes, active-version constraint trigger, and append-only audit protection.
- Add a deterministic synthetic legacy SQLite schema/fixture builder matching the current nine ORM tables.
- Add a one-shot legacy upgrade mapper that requires an explicit managed source root, creates deterministic principal/source/snapshot/version identities, preserves supported row counts/hashes, rejects external/unmappable paths, and commits the target only after validation.
- Add empty upgrade, supported upgrade, constraint/index, downgrade/forward-recovery, and metadata/schema-drift tests against disposable PostgreSQL databases.
- Keep the existing SQLite runtime and full backend behavior suite unchanged.

## Out of scope

- Switching application sessions/repositories to PostgreSQL; `DAT-003` owns the production database profile and repository adapters.
- Durable worker/job behavior, artifact publication, authentication endpoints, backup/restore drills, or production deployment Compose.
- Migrating an arbitrary user database or source tree during tests; only the declared synthetic supported schema and managed source-root mapping are accepted.
- Full-text, trigram, pgvector, external graph/search stores, or database performance tuning.
- Reading or modifying `storage/`, real credentials, or real imported repositories.

## Dependency decision

Add `psycopg[binary]>=3.3,<4.0` to `backend/requirements.txt` and regenerate `backend/requirements-lock.txt` with the locked Python 3.11/uv toolchain.

- Purpose: SQLAlchemy 2.x and Alembic PostgreSQL DBAPI driver for migration/integration tests.
- Accepted stack: PostgreSQL, SQLAlchemy, and Alembic are accepted by ADR-0001 and `stack-overview.md`; Psycopg is the narrow driver implementation.
- Compatibility: Psycopg 3.3 supports Python 3.11 and PostgreSQL 10–18; the binary extra is self-contained on supported Windows/Linux CI platforms.
- License/maintenance: LGPL-3.0-only, actively maintained by the Psycopg project.
- Security/operations: no pool extra, no embedded credentials, connection failures fail migration/test startup, and SQLAlchemy/Alembic own connection disposal.
- Lock/transitives: the universal hashed lock records `psycopg`, `psycopg-binary`, and platform markers/hashes.
- Rollback: remove the driver requirement only after removing the PostgreSQL migration/integration path; no application caller depends on it in DAT-002.

## Existing code to reuse

- `backend/app/db/models.py` is the authoritative supported legacy shape for the synthetic fixture only.
- `backend/app/db/session.py` remains the unchanged local SQLite runtime boundary.
- DAT-001 physical schema, ERD, FK catalog, indexes, transaction boundaries, and migration order are migration authority.
- The locked uv workflow and CI dependency-drift check from FND-002 remain mandatory.

## Implementation sequence

1. Add/lock Psycopg and the disposable PostgreSQL integration profile.
2. Define production metadata in dependency order and add metadata contract tests.
3. Configure Alembic and implement ordered baseline revisions from DAT-001.
4. Add fresh upgrade, downgrade-on-empty-test-database, constraint/index, and `alembic check` drift tests.
5. Build the synthetic nine-table SQLite fixture and legacy-to-production mapper with all-or-nothing validation.
6. Add supported-upgrade preservation/rejection tests and document forward recovery.
7. Run the migration suite in PostgreSQL 18.4, the complete backend suite in SQLite, and CI lock validation; record evidence and baseline/status updates.

## Data/API compatibility and migration

The application still uses the legacy SQLite metadata after this task. Production metadata is separate until DAT-003. The supported legacy mapper preserves repository IDs when valid, derives deterministic opaque index/source observation IDs, stores no host absolute path, and binds migrated facts to one immutable synthetic snapshot/version per repository. Missing managed source, invalid hashes/ranges, dangling graph edges, or unrepresentable ownership abort the target transaction with a safe report.

Baseline downgrade is supported only for an empty disposable test database. After production data import, rollback means restore the pre-migration backup or apply a reviewed forward-recovery revision; destructive downgrade is forbidden.

## Failure, security, performance, and observability requirements

- Test credentials are fixed non-production values scoped to the disposable integration service; no real credentials enter source, output, or evidence.
- Migration logs report revision/table/count/check outcomes, never source content, tokens, absolute paths, or raw database URLs.
- Each revision is transactional on PostgreSQL where DDL permits; the legacy mapper validates before commit and leaves no partial target rows.
- Migration code uses bounded batch reads/writes and deterministic stable ordering.
- The CI service uses tmpfs/disposable storage and a health check; tests create uniquely named databases and drop only those names in cleanup.
- Drift failure, unsupported legacy shape, checksum mismatch, constraint failure, or connection loss exits non-zero.

## Required tests and commands

Run from the repository root with Docker/Compose and the locked Python 3.11 environment:

```powershell
docker compose -f compose.integration.yml up -d postgres
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
backend/.venv/Scripts/python.exe -m pytest tests/migrations -q
backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini check
backend/.venv/Scripts/python.exe -m pytest tests -q
uv pip compile backend/requirements.txt --python-version 3.11 --universal --generate-hashes --output-file backend/requirements-lock.txt
git diff --exit-code -- backend/requirements-lock.txt
docker compose -f compose.integration.yml down
git diff --check -- .github/workflows/ci.yml compose.integration.yml backend/requirements.txt backend/requirements-lock.txt backend/alembic.ini backend/migrations backend/app/db/production_base.py backend/app/db/production_models backend/app/db/legacy_upgrade.py backend/scripts/migrate_legacy_sqlite.py tests/migrations docs/03-technology/stack-overview.md docs/14-implementation-baseline/source-map.md docs/14-implementation-baseline/test-inventory.md docs/16-agent-tasks/persistence/DAT-002-alembic-baseline-migration.md docs/17-runbooks/development-setup.md docs/18-production-evidence/migration-verification-report.md docs/project-status.md
```

`tests/migrations` creates and drops only databases named with the `aica_test_` prefix. CI runs the same migration suite against its pinned PostgreSQL service before the existing backend suite.

## Acceptance criteria

- The locked install contains Alembic and Psycopg with no dependency conflict or uncommitted lock regeneration diff.
- `alembic upgrade head` on a fresh PostgreSQL 18.4 database creates exactly the 35 DAT-001 tables and the declared revision head.
- Database inspection confirms all PKs, composite FKs, lifecycle/range/hash checks, partial unique indexes, 24 named access indexes, deferred cycles, and active-version/audit protections.
- Re-running `upgrade head` is a no-op; `alembic check` reports no metadata/database drift.
- Empty disposable downgrade removes only the production schema objects and upgrade succeeds again.
- The supported synthetic SQLite fixture migrates deterministically with declared row/count/hash mappings; invalid external paths, dangling relations, or checksum/range failures leave the target empty.
- Existing `app.db.models`, `app.db.session`, repository services, APIs, OpenAPI, local SQLite behavior, and complete backend suite remain unchanged.
- PostgreSQL migration tests run in CI using the pinned 18.4 image and no runtime storage or real credential is read.
- Migration evidence records commands, revisions, PostgreSQL/Alembic/Psycopg versions, table/constraint/index counts, supported-upgrade results, drift result, and forward-recovery policy.

## Rollback

Before merge, revert the task commit and remove the disposable integration service, driver, production metadata, revisions, mapper, and tests. On an empty test database, downgrade to base is verified. After migrated data exists, use backup restore or a reviewed forward revision; never run destructive baseline downgrade.

## Documentation and evidence updates

Update the stack driver inventory, source/test baselines, development setup, this task, project status, and `docs/18-production-evidence/migration-verification-report.md` with exact results.
