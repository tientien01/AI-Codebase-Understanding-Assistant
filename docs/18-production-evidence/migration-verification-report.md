# DAT-002 Migration Verification Report

Status: Locally verified; draft PR CI pending

Verified: 2026-07-13

Profile: PostgreSQL 18.4 disposable integration service on Windows/Docker

## Implemented boundary

- Separate `ProductionBase` metadata defines the 35 DAT-001 production tables; the current SQLite `Base`, session, repositories, services, and APIs are unchanged.
- Alembic head is `0001_production_baseline`; it contains static table/index/constraint DDL, deferred cyclic ownership FKs, active-version lifecycle constraint triggers, and append-only audit protection.
- Psycopg 3.3.4 is hash-locked. The integration service uses PostgreSQL 18.4 with the accepted immutable image digest.
- The supported legacy mapper accepts only the declared nine-table SQLite shape and an explicit existing managed source root. Validation failures occur before target commit; source content, absolute paths, and database URLs are not logged.

## Verified results

| Gate | Result |
| --- | --- |
| PostgreSQL / Alembic / Psycopg | 18.4 / 1.18.4 / 3.3.4 |
| Fresh upgrade | Passed; 35 production tables plus `alembic_version` |
| Alembic head | `0001_production_baseline` |
| Schema inventory | 667 PostgreSQL constraints including NOT NULL constraints; 108 total indexes; 3 non-internal protection triggers |
| Named access indexes | All 24 DAT-001 names present; partial uniqueness and supporting indexes also present |
| Zero drift | `No new upgrade operations detected.` |
| Empty downgrade / forward recovery | Passed: downgrade to base, then upgrade to head |
| Supported legacy mapping | Passed: repository, job, file, symbol, endpoint, chunk, two graph nodes, graph edge, and evidence preserved in the synthetic fixture |
| Atomic rejection | External managed path rejected; target repository count remained zero |
| Migration suite | 7 passed |
| Complete backend suite with PostgreSQL URL | 67 passed, 1 existing duplicate-ZIP warning |

## Commands

```powershell
docker compose -f compose.integration.yml up -d postgres
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
backend\.venv\Scripts\python.exe -m pytest tests/migrations -q
backend\.venv\Scripts\python.exe -m pytest tests -q
backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini check
uv pip compile backend/requirements.txt --python-version 3.11 --universal --generate-hashes --output-file backend/requirements-lock.txt
git diff --exit-code -- backend/requirements-lock.txt
```

The direct `alembic check` command was run against an upgraded disposable `aica_test_` database. The migration suite also invokes the same Alembic drift operation on a uniquely named database and drops it afterward.

## Recovery policy

Baseline downgrade is supported only for an empty disposable database and is verified as a test gate. After legacy data is imported, destructive downgrade is forbidden. Recovery requires restoring the pre-migration backup or applying a separately reviewed forward revision. Production backup/restore drill evidence belongs to the later operations task.
