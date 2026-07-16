# UI-013 Continuous Request Direction Evidence

Date: 2026-07-15

## Delivered behavior

- Changing Upstream, Downstream, or Supported full path keeps the current selected request entity instead of returning to entry points.
- The selected entity becomes the root of a fresh bounded one-hop projection in the newly selected direction.
- Direction controls are disabled while an expansion is active to prevent mixed in-flight projections.
- Terminal states now distinguish first indexed client boundaries, unmatched client calls, unresolved handlers, missing static callers, and missing static callees.
- Entry points are cleared only through the explicit reset action or entry-scope replacement.

## Verification

- `frontend\npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx`: 14 passed.
- `frontend\npm.cmd run lint`: passed.
- `frontend\npx.cmd tsc -b --pretty false`: passed.
- `frontend\npm.cmd run build`: passed; Vite transformed 145 modules and produced the production bundle.
- Focused `git diff --check`: passed.

## Remaining limitation

- A client API call remains the first indexed upstream boundary until a later intelligence task emits supported component/function-to-client-call ownership and caller relations.
