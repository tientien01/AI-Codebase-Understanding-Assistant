# Development Setup

Status: Verified local guidance; fresh install pending `FND-002`  
Owner: Project maintainer  
Verified: 2026-07-12  
Platform verified: Windows PowerShell

This runbook avoids secret files and imported runtime repositories. Dependency versions are not yet locked, so a fresh install is development-only until `FND-002` completes.

## Prerequisites

- Python 3.11. The verified existing backend environment uses Python 3.11.9.
- Node.js and npm. Node 24.14.0/npm 11.9.0 were used for the baseline; supported ranges are not yet declared.
- Git for public GitHub import development.
- Free local ports 8000 and 5173.

## Backend setup

From the repository root:

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Dependency installation requires package-index network access. Do not create or copy `.env` credentials merely to run the default fake-provider profile.

Run tests with an explicit safe collection root:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
```

Start the API:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Check `http://localhost:8000/health` and the development OpenAPI UI at `http://localhost:8000/docs`. The default profile creates local SQLite/storage state under `storage/`; this is ignored development state and not production persistence.

## Frontend setup

From `frontend/`:

```powershell
npm.cmd ci
npm.cmd run lint
npm.cmd run build
npm.cmd run dev
```

Use `npm.cmd` on Windows when the PowerShell execution policy blocks `npm.ps1`. The development server is normally `http://localhost:5173` and calls the API at `http://localhost:8000` by default.

As of the verification date, production build passes but lint has four known errors documented in `../14-implementation-baseline/test-inventory.md`.

## MVP smoke flow

1. Start backend and frontend.
2. Import the synthetic folder `tests/fixtures/fastapi_react_sample`.
3. Review preview and confirm import.
4. Start indexing and wait for a terminal status.
5. Open Overview, Code Explorer, API Explorer, Graph, Search, Impact and Assistant.
6. Ask “How does login flow work?” and open returned evidence.
7. Re-index after a controlled fixture copy change only; never edit the canonical fixture during a manual smoke run.

## Verification boundary

This setup is not yet a clean-machine guarantee. `FND-002` must declare supported Python/Node ranges, locked dependencies, reproducible install commands and CI evidence before L2.
