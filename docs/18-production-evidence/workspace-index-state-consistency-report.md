# UI-020 Workspace Index State Consistency Evidence

Status: Implemented; integration prerequisites pending
Task: `UI-020`
Verified: 2026-07-15

## Delivered outcome

- A repository with an activated version remains readable while a newer job runs. Re-index progress belongs to the job and no longer hides the active repository behind a non-indexed lifecycle.
- Status reads repair lifecycle metadata left by the previous re-index behavior when a positive active version is proven by the matching successful job.
- The frontend stale-cache bridge keeps the current positive version usable, promotes a completed job only when it advances the repository version, and never promotes an older version.
- Duplicate active submissions still return `INDEXING_ALREADY_RUNNING`.
- In the local thread profile only, an active-looking job with no in-process control after restart is retired as `INDEXING_INTERRUPTED`; this prevents a dead job from permanently locking Re-index. Durable queue/lease profiles retain their existing authority and are never inferred orphaned from process memory.

## Verification

| Gate | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/test_codebase_service.py -q` | Passed: 28 tests; 2 pre-existing warnings |
| `backend\.venv\Scripts\python.exe -m pytest tests/jobs/test_job_queue.py -q -rs` | Partial: 2 passed; 3 integration cases skipped because `TEST_POSTGRES_ADMIN_URL` / `TEST_REDIS_URL` are unavailable |
| `npm.cmd test -- --run src/App.test.tsx` | Passed: 14 tests |
| `npm.cmd test -- --run` | Passed: 88 tests across 14 files |
| `npm.cmd run lint` | Passed with 0 errors |
| `npx.cmd tsc -b --pretty false` | Passed |
| `npm.cmd run build` | Passed: Vite 8.1.0, 145 modules; JS 489.09 kB / 138.66 kB gzip; CSS 84.83 kB / 17.87 kB gzip |

## Remaining gate

Provide disposable PostgreSQL and Redis integration endpoints through the declared test variables, then rerun the queue boundary without skips. Per project verification policy, UI-020 remains `in_progress` until this prerequisite is satisfied.
