# API Explorer Interaction Verification Report

Status: Verified

Task: UI-023

Verified: 2026-07-16

Branch: `agent/api-explorer-interactions`

## Delivered behavior

- API Explorer owns a version-scoped endpoint-list query instead of borrowing Overview data.
- Endpoint read models expose an additive deterministic `endpoint_key` shared with the request-flow graph node.
- Search covers path, handler, and source file; method filters are generated from the indexed methods.
- Endpoint selection is keyboard reachable, visibly selected, persisted in `?endpoint=`, and restored by deep links/history.
- API Detail follows the selected endpoint, identifies removed/stale endpoint links, and opens exact source or a bounded API-flow projection.
- Auth/schema controls are not claimed without deterministic parser evidence.
- Generic TanStack Query cache eligibility no longer produces a global stale-data banner; only an explicit older-index state may do so.

## Verification

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/test_codebase_service.py -q` | 28 passed |
| `backend\.venv\Scripts\python.exe -m pytest tests/test_api_contract.py tests/test_codebase_service.py -q` | 35 passed |
| `backend\.venv\Scripts\python.exe -m pytest --ignore=tests/evaluation -q` | 303 passed, 31 environment-backed tests skipped |
| `npm.cmd test -- --run src/App.test.tsx src/pages/workspace/ApiExplorerPage.test.tsx src/features/server-state/serverState.test.tsx` | 29 passed |
| `npm.cmd test -- --run` | 106 passed |
| `npm.cmd run lint` | passed |
| `npx.cmd tsc -b --pretty false` | passed |
| `npm.cmd run build` | passed; existing bundle-size warning only |
| `npm.cmd run test:e2e:ui004` | all 7 cases completed with Small/Medium/Large observations; the Windows npm/web-server wrapper did not exit before the 300-second command timeout |
| `git diff --check` | passed |

The complete backend invocation reached 316 passed and 31 skipped, with 18 evaluation failures caused by the checked-out Windows fixture bytes not matching the frozen hash for `tests/fixtures/retrieval_benchmark_repo/backend/auth_service.py`. Those failures occur before scoring and do not touch files in UI-023. The only feature-related full-suite failure was expected OpenAPI drift after adding `endpoint_key`; the artifact was regenerated with `backend/scripts/export_openapi.py --write`, also recording projection-limit drift already present in server source, and the focused API contract now passes.

## GitHub verification

- Draft PR: [#40](https://github.com/tientien01/AI-Codebase-Understanding-Assistant/pull/40)
- Implementation head verified: `1fe0882`
- Both push and pull-request workflow runs passed Backend tests, AI/graph/incremental regression, Frontend quality gates, UI-004 E2E/accessibility, and UI-005 E2E/accessibility.

The first PR run exposed an existing UI-004 browser-gate mismatch also present on the latest `main` run: the test still targeted the removed generic graph heading/canvas and expected all request relations before choosing an entry point. UI-023 updates that owned gate to the accepted progressive request/dependency regions and select-before-expansion behavior; the rerun result is recorded on PR #40.
