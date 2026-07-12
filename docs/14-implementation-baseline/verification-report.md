# Phase 0 Verification Report

Status: Verified baseline  
Authority: Observed local implementation and command results  
Owner: Project maintainer  
Verified: 2026-07-12  
Profile: Windows PowerShell, existing local dependencies

This report describes the checked-out source and commands executed on the verification date. It is not a production-readiness claim.

## Environment observed

| Tool | Observed version | Use in verification |
| --- | --- | --- |
| System Python | 3.13.7 | Demonstrated that unscoped system execution lacks project dependencies |
| Backend virtualenv Python | 3.11.9 | Canonical backend verification runtime for this report |
| Node.js | 24.14.0 | Frontend lint/build runtime |
| npm | 11.9.0 | Invoked through `npm.cmd` because PowerShell blocks `npm.ps1` |

The repository has `backend/.venv` and `frontend/node_modules` locally. They are ignored development state, not reproducible release evidence. No Python project metadata/lock, Python version file, pytest configuration, CI workflow, Dockerfile, or Compose manifest was found in the inspected project paths.

## Commands and results

| Command | Result | Meaning |
| --- | --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | Pass: 52 tests, 1 expected ZIP duplicate-name warning, 38.25 s | Current targeted backend suite passes in the existing Python 3.11 environment |
| `python -m pytest -q` | Fail during collection: 7 errors | Root collection enters imported repositories under `storage/`; system Python also lacks FastAPI/Pydantic dependencies |
| `npm.cmd run lint` from `frontend/` | Fail: 4 errors | One preserved-cause error and three React hook immutability/declaration-order errors block the frontend lint gate |
| `npm.cmd run build` from `frontend/` | Pass | TypeScript and Vite production build succeeded; 85 modules transformed |
| Build output | 0.45 kB HTML, 22.66 kB CSS, 262.61 kB JS before gzip | Informative local bundle snapshot, not a performance gate |
| Documentation validation from `DOC-001` | Pass | Internal references, links, UTF-8, headings, fences, mojibake and tracked whitespace checks passed |

## Verified implementation shape

- FastAPI 0.1.0 application registers one unversioned health route and 42 `/api/v1` route handlers.
- Repository, import-session, and settings routes are concentrated in `api/v1/routes/repositories.py`; API DTOs are concentrated in one schema module with 63 `BaseModel` classes.
- SQLite is the default database. Startup uses SQLAlchemy `create_all` plus manual SQLite `ALTER TABLE` compatibility patches.
- Nine ORM models cover repositories, jobs, files, symbols, endpoints, chunks, graph nodes/edges, and evidence.
- Background indexing uses daemon `Thread` plus process-local `Event` controls. Job records persist, but live pause/resume/cancel control does not survive process loss.
- Full/incremental indexing, stale evidence, graph projections, impact, deterministic sparse-vector retrieval, evidence validation, and a bounded heuristic assistant are present and covered by current unit/integration-style tests.
- The frontend exposes all planned navigation surfaces, but uses controller-driven page state rather than React Router/TanStack Query. Evaluation and settings are partial/static surfaces.

## Baseline blockers

| Priority | Blocker | Consequence | Owning future task |
| --- | --- | --- | --- |
| P0 | No scoped pytest configuration | Root test command executes untrusted/imported repository test modules | `FND-002` or a dedicated test-foundation task |
| P0 | Unlocked Python dependencies/project metadata | Fresh install is not reproducible | `FND-002` |
| P0 | `create_all` and manual schema patches | No supported production migration history/drift guarantee | `DAT-002` |
| P0 | Process-local worker controls | Restart/recovery/cancel are not production durable | `JOB-002..004` |
| P1 | Frontend lint has four errors | Frontend CI gate cannot pass | future scoped frontend foundation task |
| P1 | No frontend tests or E2E configuration | UI behavior is not regression protected | `UI-001..005` foundation |
| P1 | No CI/container/deployment baseline | L2/L3 reproducibility is unproven | `FND-002`, `OPS-002` |
| P1 | No generated/checked OpenAPI artifact | Markdown/API implementation drift is not automatically detected | `FND-003` |

## Reproduction boundary

The passing backend result depends on the existing ignored virtualenv. A fresh-machine install was not attempted because `DOC-002` does not authorize network access, dependency installation, or lockfile changes. `FND-002` must turn this local success into reproducible evidence.
