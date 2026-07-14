# UI-005 Evaluation, Settings, and Readiness Evidence

Status: Verified

Task: `UI-005`

Verified: 2026-07-14

## Delivered boundary

- Settings uses global TanStack Query ownership for authenticated `GET /api/v1/settings` and `GET /api/v1/settings/ignore-patterns` reads.
- The UI renders only the allowlisted indexing limits/profile, provider/model names, configured booleans, secret-scanning boolean and effective ignore patterns. Unexpected response fields are not rendered.
- Provider credentials are never requested, stored in route state or displayed.
- Settings mutations and provider tests are explicitly unavailable because their accepted API routes are not implemented.
- Evaluation keeps the selected repository lifecycle, active index and current index-job facts visible while declaring dataset/run/status/result APIs unavailable.
- Offline deterministic CI evidence is described as regression protection and never impersonates a user-triggered evaluation run.
- Shared async presentation adds typed `limited` and `unavailable` states while preserving permission, retry, cancellation, refreshing and stale behavior.

No backend route, schema, service, configuration, evaluation dataset/gate, database, storage, provider execution, user preference or dependency changed.

## Verification results

| Gate | Observed result |
| --- | --- |
| Clean dependency install | `npm.cmd ci` added 239 locked packages successfully |
| Focused frontend | 22 passed across UI-005 workspace, server-state and application routing suites |
| Full frontend | 51 passed across 8 files |
| Lint | Passed with zero errors or warnings |
| TypeScript | `npx.cmd tsc -b --pretty false` passed |
| Production build | Passed; 131 transformed modules |
| UI-005 browser E2E | 4 passed: Settings success, permission, retry recovery; Evaluation repository/index context and unavailable capability |
| Accessibility/keyboard | Settings and Evaluation axe WCAG serious/critical = 0; Tab reached an actionable navigation target |
| UI-004 regression | 6 Chromium tests passed after the shared Playwright configuration change |
| Lock review | `frontend/package-lock.json` unchanged; no dependency added or upgraded |
| Diff hygiene | `git diff --check -- .github frontend docs` passed locally |
| Named CI gate | `Frontend UI-005 E2E and accessibility` passed for commit `2f22d77` ([GitHub Actions evidence](https://github.com/tientien01/AI-Codebase-Understanding-Assistant/actions/runs/29334971200/job/87091826611)) |

## Bundle observations

| Asset | UI-004 | UI-005 | Delta |
| --- | ---: | ---: | ---: |
| JS | 374.30 kB / 114.36 kB gzip | 378.67 kB / 115.46 kB gzip | +4.37 kB / +1.10 kB gzip |
| CSS | 36.15 kB / 8.59 kB gzip | 37.19 kB / 8.79 kB gzip | +1.04 kB / +0.20 kB gzip |
| Transformed modules | 131 | 131 | 0 |

No accepted Phase 6 route-load, interaction, long-task, memory or bundle threshold exists, so these exact observations do not establish release performance acceptance.

## Remaining product boundaries

- Public evaluation datasets/runs/results, run persistence, mutable allowlisted settings, provider tests, operational `/health/ready`, accepted performance budgets and Phase 6 release qualification remain separate authorized work.
