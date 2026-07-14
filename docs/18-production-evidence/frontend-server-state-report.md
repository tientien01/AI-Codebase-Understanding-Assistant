# UI-002 Frontend Server-State Evidence

Status: Verified locally; pending review and merge

Task: `UI-002`

Verified: 2026-07-14

## Delivered boundary

- One application `QueryClientProvider` owns current repository/workspace server state.
- Typed API functions forward TanStack Query cancellation signals for repository, status, overview, graph, file, evidence, search and import-preview reads.
- Query keys carry repository and active index-version identity. Import previews carry import-session identity; chat transcripts are repository/version scoped in the query cache.
- Re-index, job control, delete, graph expansion, impact, chat and import actions use mutations. Successful actions invalidate or remove only documented affected list/status/repository/version families.
- Retry is limited to two attempts for classified transport, timeout, HTTP 429 and 5xx failures. Permission, not-found and validation failures are terminal. Retry delay is capped and uses deterministic jitter.
- Index polling is query-owned and returns `false` for terminal jobs or hidden documents. Existing focus/reconnect behavior may refresh stale active queries.
- Active surfaces project loading, refreshing, stale, empty, permission-denied, retryable, terminal, cancelled and unavailable states without replacing safe same-key cached data during refresh.

Transient form inputs, selected upload files, upload progress and route-independent display choices remain local interaction state. React Router remains authoritative for canonical workspace identity. No backend endpoint, schema, route contract or persisted data changed.

## Dependency and lock evidence

| Item | Observed result |
| --- | --- |
| Runtime dependency | `@tanstack/react-query@5.101.2` (MIT) |
| Additional installed packages | 2 TanStack packages; no additional transport/state dependency |
| Node/npm | Node `v24.14.0`; npm `11.9.0` |
| `package-lock.json` SHA-256 before/after `npm ci` | `D41AAC6F255DB4CE7A35BF7E43B44AC4518AAF2E2EC6DF323A4450C3BC86CD91` / identical |
| npm audit at dependency installation | 235 packages audited; 0 vulnerabilities |

## Verification results

| Gate | Result |
| --- | --- |
| Targeted Vitest command | 22 tests passed across 4 files |
| Full `npm.cmd run test` | 38 tests passed across 5 files |
| `npm.cmd run lint` | Passed with 0 errors |
| `npx.cmd tsc -b` | Passed |
| `git diff --check -- frontend docs` | Passed |
| Clean `npm.cmd run build` | Passed from detached commit `3c2987f` without local environment files |

Focused tests cover owner/version key separation, request cancellation, retry classification/delay, terminal/hidden polling, async-state projection, same-key cached-data retention, scoped graph invalidation, import query ownership and application retry recovery.

## Bundle observation

| Asset | UI-001 baseline | UI-002 | Delta |
| --- | ---: | ---: | ---: |
| JS | 311.75 kB / 96.66 kB gzip | 356.06 kB / 109.35 kB gzip | +44.31 kB / +12.69 kB gzip |
| CSS | 23.32 kB / 5.71 kB gzip | 23.78 kB / 5.83 kB gzip | +0.46 kB / +0.12 kB gzip |
| Transformed modules | 92 | 131 | +39 |

No accepted Phase 6 release bundle threshold exists, so this report records the measured cost without treating it as release qualification.

## Remaining gaps

UI-002 does not add bounded/truncated graph projection, architecture/tour/diff surfaces, real evaluation/settings/status integrations, MSW contracts, automated accessibility checks, Playwright critical flows or accepted performance budgets. Those remain UI-003 through UI-005 and Phase 6 release work. Symbol and conversation-history deep links still require public read models; the current chat transcript is client-session scoped and query-cache owned.
