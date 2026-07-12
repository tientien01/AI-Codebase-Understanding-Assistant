# Local Development Troubleshooting

Status: Verified development guidance  
Owner: Project maintainer  
Verified: 2026-07-12

## Pytest collects imported repositories

**Symptom:** root `python -m pytest` reports import errors under `storage/repositories/` or `storage/uploads/`.

**Cause:** there is no checked pytest configuration restricting discovery, and imported repositories may contain `test_*.py` files.

**Safe action:**

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
```

Do not execute, repair, or inspect the imported repository tests. A future foundation task must add `testpaths = tests` and explicit exclusions.

## Backend imports are missing

**Symptom:** `ModuleNotFoundError` for FastAPI, Pydantic, SQLAlchemy or related packages.

**Cause:** the system Python is being used instead of `backend/.venv`, or dependencies were not installed.

**Check:**

```powershell
backend\.venv\Scripts\python.exe --version
backend\.venv\Scripts\python.exe -m pytest tests -q
```

Do not mix a global Python 3.13 environment with the verified Python 3.11 virtualenv.

## PowerShell blocks npm

**Symptom:** `npm.ps1 cannot be loaded because running scripts is disabled`.

**Action:** invoke the Windows command shim:

```powershell
npm.cmd --version
npm.cmd run build
```

Changing the machine execution policy is unnecessary for this project workflow.

## Frontend lint fails

The verified baseline has four lint errors in `src/api/client.ts` and `src/hooks/useImportController.ts`. Build may still pass; do not interpret that as a complete frontend gate. Fix them only through an approved frontend task with behavior checks.

## Local database/schema surprises

The current backend uses SQLite `create_all` plus compatibility `ALTER TABLE` patches. If local state disagrees with source, preserve it before diagnosis. Do not delete `storage/` broadly. Use a scoped approved task or create a clean isolated development profile; production migration behavior does not exist yet.

## Index job appears stuck after API restart

The current worker/control state is process-local. A persisted job row does not mean its daemon thread survived. Do not manually mark it successful. Preserve the previous active index, record job/repository IDs, and treat restart recovery as unsupported until the durable-worker phase.

## Assistant does not call a real model

The default provider is `fake`; this intentionally exercises deterministic grounded fallback. Do not add real keys to source, docs, logs, or tests. Provider configuration and credential handling require the accepted security/settings path.
