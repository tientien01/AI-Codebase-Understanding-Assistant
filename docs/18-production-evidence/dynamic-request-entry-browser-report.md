# UI-014 Dynamic Request Entry Browser Evidence

Date: 2026-07-15

## Delivered behavior

- All, Server, and Client controls now disclose repository-backed counts rather than presenting uncounted exhaustive-looking tabs.
- Request-flow seed projections honor deterministic offset pages and report the remaining entry count.
- The browser displays `loaded of total`, chooses a 24/32/48 item batch from viewport width, and offers an explicit Load next action.
- Loaded pages accumulate in the entry browser while the graph canvas remains focused on a selected request path.
- Entry-scope refreshes update browser data without clearing the current path; only the explicit reset returns to the loaded entry collection.
- Search wording explicitly limits the current implementation to loaded entries rather than implying global search.
- The HTTP route and request schema now share the same paging bounds, preventing adaptive batches above 24 or offsets above 220 from being rejected as `422 Request failed`.

## Verification

- `backend\.venv\Scripts\python.exe -m pytest ..\tests\test_graph_projection.py -q`: 14 passed, with one third-party OpenTelemetry deprecation warning.
- `backend\.venv\Scripts\python.exe -m pytest ..\tests\test_api_contract.py -q -k graph_projection`: 1 passed and 6 deselected, with one third-party OpenTelemetry deprecation warning.
- `frontend\npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx`: 15 passed.
- `frontend\npm.cmd run lint`: passed.
- `frontend\npx.cmd tsc -b --pretty false`: passed.
- `frontend\npm.cmd run build`: passed; Vite transformed 145 modules and produced the production bundle.
- Focused `git diff --check`: passed.

## Remaining follow-up

- Server-backed global entry search, route-prefix grouping, virtualized list presentation, and FastAPI router-prefix reconstruction remain separate follow-up work. The current browser truthfully searches only loaded entries.
