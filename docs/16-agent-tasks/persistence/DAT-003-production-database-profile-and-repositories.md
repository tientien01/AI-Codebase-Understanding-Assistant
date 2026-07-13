---
id: DAT-003
title: Add the production database profile and repository adapters
status: completed
priority: P0
phase: 1
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [DAT-002]
requirements: []
contracts:
  - docs/03-technology/environment-and-configuration.md
  - docs/03-technology/stack-profiles.md
  - docs/04-domain-and-data/postgresql-physical-schema.md
  - docs/04-domain-and-data/identity-and-artifact-contract.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/stack-overview.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/core/config.py
  - backend/app/db/production_session.py
  - backend/app/services/application/container.py
  - backend/app/services/repositories/repository_port.py
  - backend/app/services/repositories/repository_store.py
  - backend/app/services/repositories/production_repository_store.py
  - backend/app/services/repositories/repository_service.py
  - backend/app/services/evidence/evidence_service.py
  - backend/app/services/indexing/indexing_service.py
  - backend/app/services/indexing/indexing_job_service.py
  - tests/persistence/**
  - .github/workflows/ci.yml
  - docs/03-technology/environment-and-configuration.md
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/16-agent-tasks/persistence/DAT-003-production-database-profile-and-repositories.md
  - docs/17-runbooks/development-setup.md
  - docs/18-production-evidence/postgresql-repository-integration-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/app/db/models.py
  - backend/app/db/session.py
  - backend/migrations/**
  - backend/app/api/**
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - The default local profile retains the current SQLite store and complete behavior suite.
  - APP_ENV=production accepts only a PostgreSQL DATABASE_URL and verifies Alembic head before constructing the application container.
  - The PostgreSQL repository adapter uses ProductionBase metadata without create_all and enforces repository/index ownership in integration tests.
  - Production configuration and logs do not expose database credentials or imported absolute paths.
evidence_outputs:
  - docs/18-production-evidence/postgresql-repository-integration-report.md
---

# Task DAT-003 — Add the production database profile and repository adapters

## Context

DAT-002 created the PostgreSQL schema and migration boundary, while the application composition root still constructs the SQLite `RepositoryStore` unconditionally. Production startup therefore has no fail-fast database profile and cannot select a PostgreSQL repository adapter.

## Objective

Add an explicit local/production database profile and a PostgreSQL repository adapter behind a typed port, preserving the existing SQLite default and public API behavior.

## In scope

- Add `APP_ENV` validation for `test`, `local`, and `production`; production requires a PostgreSQL URL.
- Create a production engine/session boundary that verifies the database is at Alembic head and never calls `create_all`.
- Extract the repository-store interface as a typed protocol and select its adapter in the application composition root.
- Implement PostgreSQL repository metadata and active-version observation persistence needed by current repository/evidence reads.
- Add disposable PostgreSQL integration tests for selection, fail-fast startup, CRUD, ownership, rollback, and local SQLite regression.

## Out of scope

- Durable job claim/lease/retry behavior (`JOB-001` onward), immutable artifact publication (`IDX-001` onward), queue/worker changes, auth, deployment Compose, or backup/restore.
- Changing the public API, Alembic schema, current SQLite models/session, or reading real source repositories and credentials.

## Existing code to reuse

- `ProductionBase` and production tables from DAT-002.
- The current `RepositoryStore` remains the local SQLite adapter.
- `ApplicationContainer` remains the sole adapter selection boundary.

## Implementation sequence

1. Add validated profile configuration and production session/head verification.
2. Define the repository port and update dependency annotations/composition.
3. Implement production repository metadata and immutable observation transactions.
4. Add PostgreSQL integration and local compatibility tests.
5. Run the migration, persistence, complete backend, lock, and diff gates; record evidence.

## Data/API compatibility and migration

No schema revision is added. A production database must already be at DAT-002 Alembic head. Local startup remains SQLite-compatible. Production startup fails before serving requests when the URL is not PostgreSQL, connectivity fails, or the revision is not head.

## Failure, security, performance, and observability requirements

- Never log or return raw database URLs; errors identify only the profile and stable failure category.
- Repository writes are transactional and bind every observation to repository plus opaque index-version identity.
- No host absolute path is persisted in PostgreSQL; managed paths are reconstructed only beneath configured storage roots.
- Integration tests create/drop only `aica_test_` databases.

## Required tests and commands

```powershell
docker compose -f compose.integration.yml up -d postgres
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
backend\.venv\Scripts\python.exe -m pytest tests/persistence -q
backend\.venv\Scripts\python.exe -m pytest tests/migrations -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --exit-code -- backend/requirements-lock.txt
git diff --check
docker compose -f compose.integration.yml down
```

## Acceptance criteria

- Default construction selects SQLite and all existing tests remain unchanged.
- Production construction selects PostgreSQL only after connectivity and Alembic-head verification.
- Repository create/list/update/delete and active-version observation round trips pass on PostgreSQL 18.4 without `create_all`.
- Cross-repository/version observations fail transactionally and leave no partial rows.
- No migration or dependency diff is introduced.

## Rollback

Revert DAT-003; local SQLite remains the default. Do not downgrade the DAT-002 database schema.

## Documentation and evidence updates

Update configuration, source/test baselines, development setup, project status, and the PostgreSQL repository integration report.
