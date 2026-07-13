# Development Setup

Status: Clean local and PostgreSQL integration profiles verified
Owner: Project maintainer  
Verified: 2026-07-13
Platform verified: Windows PowerShell

This runbook avoids secret files and imported runtime repositories. Python and npm dependency graphs are locked; local clean installation is verified. `FND-002` remains incomplete until the committed GitHub Actions workflow supplies immutable CI evidence.

## Prerequisites

- Python `>=3.11,<3.12`. The verified clean backend environment uses Python 3.11.9; `.python-version` declares the supported minor.
- `uv==0.11.28`, installed from the official release/Python package source and verified with `uv --version`.
- Node.js `>=24,<25` and npm `>=11,<12`. `.nvmrc` declares Node 24; Node 24.14.0/npm 11.9.0 were verified.
- Git for public GitHub import development.
- Free local ports 8000 and 5173. Port 55432 is additionally required only for the Docker PostgreSQL integration profile.

## Backend setup

From the repository root:

```powershell
uv venv backend\.venv --python 3.11
uv pip sync --python backend\.venv\Scripts\python.exe backend\requirements-lock.txt
uv pip check --python backend\.venv\Scripts\python.exe
```

Dependency installation requires package-index network access. The lock includes hashes and must not be regenerated during routine setup. Do not create or copy `.env` credentials merely to run the default fake-provider profile.

Run both the targeted suite and the root collection check:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
backend\.venv\Scripts\python.exe -m pytest -q
```

Start the API:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Check `http://localhost:8000/health` and the development OpenAPI UI at `http://localhost:8000/docs`. The default profile creates local SQLite/storage state under `storage/`; this is ignored development state and not production persistence.

## PostgreSQL migration profile

The normal local application still uses SQLite and does not require Docker. Start the disposable PostgreSQL profile only for migration/integration work:

```powershell
docker compose -f compose.integration.yml up -d postgres
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
backend\.venv\Scripts\python.exe -m pytest tests/migrations -q
docker compose -f compose.integration.yml down
```

The tests create and drop only databases whose names start with `aica_test_`. PostgreSQL may instead run as a native service or remote managed database when the corresponding non-secret URL is supplied; Docker is not a production runtime requirement.

Alembic reads `TEST_DATABASE_URL` for an explicitly selected disposable database, then `DATABASE_URL`. A fresh production-schema upgrade is:

```powershell
$env:DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST/DATABASE'
backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

Do not run baseline downgrade after data import. Restore the pre-migration backup or apply a reviewed forward-recovery revision.

## Frontend setup

From `frontend/`:

```powershell
npm.cmd ci
npm.cmd run test
npm.cmd run lint
npm.cmd run build
npm.cmd run dev
```

Use `npm.cmd` on Windows when the PowerShell execution policy blocks `npm.ps1`. The development server is normally `http://localhost:5173` and calls the API at `http://localhost:8000` by default.

As of the verification date, the four targeted tests, lint, TypeScript, and production build pass from a clean npm install.

## Lock maintenance

Routine installs consume locks. A reviewed dependency update regenerates the Python lock from the repository root with pinned `uv`:

```powershell
uv pip compile backend/requirements.txt --python-version 3.11 --universal --generate-hashes --output-file backend/requirements-lock.txt
```

Re-run the command without an upgrade flag and verify the lock hash is unchanged. Any resolved version change requires dependency authorization, compatibility review, full gates, and updated install evidence. npm dependency changes must use an exact reviewed package version and commit the resulting `package-lock.json`.

## MVP smoke flow

1. Start backend and frontend.
2. Import the synthetic folder `tests/fixtures/fastapi_react_sample`.
3. Review preview and confirm import.
4. Start indexing and wait for a terminal status.
5. Open Overview, Code Explorer, API Explorer, Graph, Search, Impact and Assistant.
6. Ask “How does login flow work?” and open returned evidence.
7. Re-index after a controlled fixture copy change only; never edit the canonical fixture during a manual smoke run.

## Verification boundary

This setup is verified in a clean local Python environment and through `npm ci`. It becomes the CI-backed development baseline only after the committed workflow passes and its immutable run is linked from `development-install-report.md`.
