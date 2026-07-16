# UI-012 Progressive Request Flow Evidence

Date: 2026-07-15

## Delivered behavior

- Request Flow opens with deterministic server-endpoint and client API-call entry points instead of a broad repository call-site projection.
- Entry points disclose handler-resolution or client-match status and measured index coverage.
- Selecting an entry point loads one bounded static-support hop. Selecting an already visible node only opens its inspector; `Continue from here` performs the next expansion.
- Upstream, Downstream and Supported full path reset incompatible accumulated path state.
- The primary canvas requests only endpoint, API-call, function and method nodes with `calls_api`, `exposes_endpoint` and `calls` relations. Indexed call-site evidence is not deleted, but it is excluded from this default presentation.
- Entry-point reset, search, zoom, fit, same-view inspector and an accessible complete relation list are available without changing tabs.

## Verification

- `backend\.venv\Scripts\python.exe -m pytest ..\tests\test_graph_projection.py -q`: 13 passed, with one third-party OpenTelemetry deprecation warning.
- `frontend\npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx`: 13 passed.
- `frontend\npm.cmd run lint`: passed.
- `frontend\npx.cmd tsc -b --pretty false`: passed.
- `frontend\npm.cmd run build`: passed; Vite transformed 145 modules and produced the production bundle.
- Focused `git diff --check`: passed.

## Remaining limitations

- This view presents deterministic static-index support, not runtime execution order or a complete request trace.
- Client-call matching and endpoint-handler resolution remain limited by existing producers; unmatched or unresolved entities are shown honestly as partial coverage.
- Call-site nodes remain in the compatibility graph for other views and evidence workflows, but UI-012 does not add new call-site-to-callable resolution.
