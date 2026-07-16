# UI-019 Unified Navigation and Index Readiness Evidence

Status: Verified locally
Task: `UI-019`
Verified: 2026-07-15

## Delivered outcome

- Management and workspace shells now use one `aica:sidebar` local preference, one accessible toggle pattern and the same compact icon-rail CSS. The previous workspace-only preference is read as a migration fallback.
- Collapsed state survives navigation between Projects/Index Jobs/Settings and repository workspace routes.
- Settings was removed from repository workspace navigation. The canonical global `/settings` destination remains in management navigation.
- A successful terminal index status bridges stale repository-list cache only when repository ownership matches and a positive integer `index_version` is present. The existing terminal-status repository query invalidation remains the durable refresh path.
- `100%` progress by itself, running/failed/cancelled status, repository mismatch and missing/invalid version never authorize workspace access.

## Verification

| Gate | Result |
| --- | --- |
| `npm.cmd test -- --run src/components/layout/AppShell.test.tsx src/App.test.tsx` | Passed: 15 tests across 2 files |
| `npm.cmd test -- --run` | Passed: 86 tests across 14 files |
| `npm.cmd run lint` | Passed with 0 errors |
| `npx.cmd tsc -b --pretty false` | Passed |
| `npm.cmd run build` | Passed: Vite 8.1.0, 145 modules; JS 488.76 kB / 138.58 kB gzip; CSS 84.83 kB / 17.87 kB gzip |
| Declared `git diff --check` scope | Passed; Git emitted Windows CRLF conversion warnings only |

Focused coverage verifies collapse/expand accessibility, cross-shell persistence, global-only Settings navigation, completed-version workspace opening through stale repository data, and rejection of progress-only, failed, cancelled and versionless status.

## Compatibility and limitations

No backend, API schema, dependency or route vocabulary changed. Reconciliation does not manufacture an index from progress: it accepts only the existing server terminal success plus active index version contract and is replaced naturally when the repository-list query refresh completes.
