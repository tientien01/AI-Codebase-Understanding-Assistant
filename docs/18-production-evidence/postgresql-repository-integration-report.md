# DAT-003 PostgreSQL Repository Integration Report

Status: Locally verified; CI publication pending

Verified: 2026-07-13

Profile: PostgreSQL 18.4 disposable integration service

## Implemented boundary

- `APP_ENV=production` requires PostgreSQL and fails before application composition when connectivity or the Alembic revision is invalid.
- The composition root selects a typed `RepositoryStorePort`: SQLite remains the local adapter and PostgreSQL is selected only for production.
- The PostgreSQL adapter writes repository/source/snapshot/version/observation/evidence records through `ProductionBase` without `create_all` or a schema change.
- Host absolute paths are not persisted. Runtime paths are reconstructed beneath `REPOSITORY_STORAGE_ROOT/<repository-id>/source`.
- Snapshot identities include the deterministic inventory checksum. Graph ownership failures rollback the whole repository transaction.

## Results

| Gate | Result |
| --- | --- |
| DAT-003 persistence suite | 7 passed |
| DAT-002 migration regression plus persistence | 14 passed |
| Complete backend suite | 74 passed, 1 existing duplicate-ZIP warning |
| Local profile regression | Existing SQLite service and codebase tests passed |
| Fail-fast startup | Non-PostgreSQL configuration and non-head database rejected |
| Repository/evidence CRUD | Create, list, observation load, evidence save/stale/load, and delete passed |
| Job target lifecycle | Compatibility job target persisted as `building` and finalized as `active` with its repository version |
| Transaction rollback | Dangling graph edge left the repository table empty |
| Managed source boundary | External source root rejected before a database write |

## Commands

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

## Remaining boundary

DAT-003 does not claim durable worker/job semantics or immutable artifact payload publication. `JOB-001` owns job/version/artifact state transitions, and `IDX-001` owns artifact manifests/store behavior. PostgreSQL production profile support does not make the release production-ready by itself.
