# Phase 0 Verification Report

Status: Verified baseline  
Authority: Observed local implementation and command results  
Owner: Project maintainer  
Verified: 2026-07-13
Profile: Windows PowerShell, existing local dependencies

This report describes the checked-out source and commands executed on the verification date. It is not a production-readiness claim.

## Environment observed

| Tool | Observed version | Use in verification |
| --- | --- | --- |
| System Python | 3.13.7 | Demonstrated that unscoped system execution lacks project dependencies |
| Backend virtualenv Python | 3.11.9 | Canonical backend verification runtime for this report |
| Node.js | 24.14.0 | Frontend lint/build runtime |
| npm | 11.9.0 | Invoked through `npm.cmd` because PowerShell blocks `npm.ps1` |
| uv | 0.11.28 | Generated and installed the hashed Python 3.11 lock |

The repository now declares Python 3.11 and Node 24, has Python project metadata, hashed Python and npm locks, scoped Pytest configuration, and a minimal pinned GitHub Actions workflow. Clean local install evidence passed; immutable GitHub Actions evidence remains pending. Dockerfile and Compose manifests are still absent.

## Commands and results

| Command | Result | Meaning |
| --- | --- | --- |
| Clean `uv pip sync` + `uv pip check` | Pass: 107 packages, no baseline version drift, all compatible | Python 3.11 install is reproducible from the hashed lock |
| Clean `python -m pytest tests -q` | Pass: 52 tests, 1 expected ZIP duplicate-name warning, 38.95 s | Targeted backend suite passes from the lock |
| Clean root `python -m pytest -q` | Pass: the same 52 tests and warning, 43.08 s | Root collection is scoped to project tests and excludes `storage/` |
| `npm.cmd run test` from `frontend/` | Pass: 4 tests across 2 files | Targeted timeout-cause and folder/ZIP/GitHub automatic-preview behavior is now protected |
| `npm.cmd run lint` from `frontend/` | Pass: 0 errors | The four-error baseline was cleared by `FND-005` without new rule suppression |
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
| P0 | `create_all` and manual schema patches | No supported production migration history/drift guarantee | `DAT-002` |
| P0 | Process-local worker controls | Restart/recovery/cancel are not production durable | `JOB-002..004` |
| P1 | Frontend coverage is limited to four foundation tests; no E2E configuration | Broad UI behavior is not regression protected | `UI-001..005` foundation |
| P1 | CI workflow is defined but has no immutable successful run yet; containers/deployment remain absent | CI/L2 evidence and L3 deployment reproducibility are unproven | `FND-002`, `OPS-002` |
| P1 | No generated/checked OpenAPI artifact | Markdown/API implementation drift is not automatically detected | `FND-003` |

## Reproduction boundary

The clean local backend environment and npm install passed from committed lock content. This verifies lock completeness on Windows/Python 3.11/Node 24, not a second operating system or immutable CI run. `FND-002` remains incomplete until the GitHub Actions workflow passes on the committed revision.
