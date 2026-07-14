# UI-001 Frontend Navigation Report

Status: Verified task evidence; not release approval

Task: `UI-001`

Verified: 2026-07-14

Implementation revision: `09b9e2d`

Profile: Windows, Node 24.14.0, npm 11.9.0, Vite 8.1.0

## Verified outcome

React Router now owns browser navigation for the accepted canonical management and repository workspace routes. One deterministic route boundary parses and builds opaque repository, source, symbol, endpoint, graph, impact, search, conversation and evidence identities. Direct source and evidence routes load only their URL-owned repository context; browser history is preserved; unsafe/malformed URLs, missing repositories and unusable repositories show explicit recovery instead of unrelated content.

Symbol and conversation identities are routable but deliberately show unavailable recovery states because their public bounded read models are not present. This avoids fabricating or replaying unrelated data and leaves those read models to their owning later tasks.

## Dependency and lock evidence

- Added exactly `react-router-dom@7.18.1` as the accepted runtime router.
- npm metadata reported MIT licensing and Node `>=20`; the project remains locked to Node `>=24,<25`.
- Deterministic transitive additions are `react-router@7.18.1`, `cookie@1.1.1`, and `set-cookie-parser@2.7.2`.
- `npm install` reported zero known vulnerabilities; this is install-time output, not a release vulnerability scan.
- `npm ci` preserved package-lock SHA-256 `6502B2385441EC553A52F41D2C37E91F7E782BDC77A7EB91290F457E7DBA5D09`.

## Test and build evidence

| Gate | Result |
| --- | --- |
| `npm.cmd run test -- src/routing/routes.test.ts src/App.test.tsx` | Passed: 23 tests across 2 files |
| `npm.cmd run test` | Passed: 27 tests across 4 files |
| `npm.cmd run lint` | Passed with 0 errors |
| `npx.cmd tsc -b` | Passed |
| Clean `npm.cmd run build` | Passed: 92 modules transformed |
| Vite preview canonical source deep link | HTTP 200; returned the SPA shell |
| `git diff --check -- frontend docs` | Passed |

The application tests cover the legacy-root redirect, canonical direct source/line restoration, repository-owned evidence loading, URL-owned search state, missing-repository fail-closed behavior, unsafe source-path recovery, and browser back/forward navigation. The route matrix additionally covers encoded identities, all stateful URL builders, symbol/conversation/evidence detail classification, malformed identifiers, unsafe paths, invalid numeric values and unsupported graph views.

The clean build and HTTP smoke ran from a detached worktree without ignored backend environment files. The tested deep link was `/repositories/repo-1/code?path=src%2Fauth.ts&line=2`; Vite preview returned the built `index.html` shell with HTTP 200.

## Bundle observation

| Artifact | `origin/main` before UI-001 | UI-001 | Change |
| --- | ---: | ---: | ---: |
| JavaScript | 262.62 kB / 79.90 kB gzip | 311.75 kB / 96.66 kB gzip | +49.13 kB / +16.76 kB gzip |
| CSS | 22.66 kB / 5.53 kB gzip | 23.32 kB / 5.71 kB gzip | +0.66 kB / +0.18 kB gzip |
| Transformed modules | 85 | 92 | +7 |

No accepted Phase 6 numeric bundle threshold exists, so this report records the measured cost without inventing a pass threshold. Route-level lazy loading remains an available later optimization after representative route-load budgets are accepted.

## Compatibility and remaining gaps

- Existing backend endpoints, schemas, payloads and persisted data are unchanged.
- Existing import, indexing, project, workspace, search, impact, graph, assistant and evidence page components remain the compatibility surface.
- `/` redirects to canonical `/projects`; other invalid locations do not silently redirect.
- `UI-002` still owns TanStack Query/server-state migration and the complete async-state matrix.
- `UI-003` through `UI-005` still own bounded graph UX, architecture/tour/diff experiences, and real evaluation/settings/status integration.
- MSW contracts, accessibility automation, critical Playwright flows and accepted performance budgets remain open Phase 6 evidence.

This report verifies UI-001 only. It does not claim Phase 6 completion or L3 production readiness.
