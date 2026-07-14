# UI-004 Architecture, Tour, Graph, and Impact Evidence

Status: Local implementation gates verified; Evidence-backed UX E2E and accessibility automation pending

Task: `UI-004`

Verified: 2026-07-14

## Delivered boundary

- Graph Explorer keeps the UI-003 server projection authoritative and renders every returned node and edge in a deterministic client presentation.
- Nodes are grouped into disclosed architecture layers; SVG edges retain direction and support styling; selecting a node focuses its immediate neighborhood without removing any result.
- Zoom/fit controls, minimap summary, type legend, selected-entity tabs and source/focus/impact actions use existing React and CSS dependencies.
- The complete native relation list remains available and selection can be performed without the visual canvas.
- Motion is limited to focus/edge flow and is disabled by `prefers-reduced-motion`.
- Overview architecture and guided-tour steps derive only from current stack, endpoint, module and important-file reasons. Missing tour entrypoints remain unavailable instead of being invented.
- Impact presents current results as direct, inferred and unknown; missing relations remain visible and historical comparison is explicitly unavailable because the compatibility API has no version snapshots.
- The supplied screenshots and HTML/CSS were preserved as visual references. The generated UI-004 concept is stored at `docs/09-frontend-and-ux/references/ai-codebase-ui-reference/assets/concepts/ui-004-graph-explorer.png`.

No API, database, graph fact, dependency, lock, indexing, retrieval, storage or historical-version behavior changed.

## Verification results

| Gate | Observed result |
| --- | --- |
| Clean dependency install | `npm.cmd ci` added 234 locked packages successfully |
| Targeted frontend | 14 passed across `GraphPage`, UI-004 workspace and application routing suites |
| Full frontend | 45 passed across 7 files |
| Lint | Passed with zero errors or warnings |
| TypeScript | `npx.cmd tsc -b --pretty false` passed |
| Production build | Passed; 131 transformed modules |
| Lock stability | `frontend/package-lock.json` unchanged |
| Diff hygiene | `git diff --check -- frontend docs` passed |

## Graph and bundle observations

The existing maximum-projection component fixture still renders all 220 returned nodes and 219 returned relations. UI-004 additionally asserts one SVG edge per returned relation and preserves the full relation-list count after selection. These jsdom observations are regression evidence, not a browser interaction or memory threshold.

| Asset | UI-003 | UI-004 | Delta |
| --- | ---: | ---: | ---: |
| JS | 362.30 kB / 110.98 kB gzip | 374.22 kB / 114.34 kB gzip | +11.92 kB / +3.36 kB gzip |
| CSS | 25.18 kB / 6.08 kB gzip | 36.15 kB / 8.59 kB gzip | +10.97 kB / +2.51 kB gzip |
| Transformed modules | 131 | 131 | 0 |

No accepted Phase 6 bundle threshold exists, so no release pass/fail is inferred from these values.

## Remaining mandatory evidence

- The task-register Evidence-backed UX E2E flow has no Playwright harness or approved fixture.
- Automated accessibility, focus restoration, contrast and reduced-motion browser checks remain absent.
- Representative Small/Medium/Large browser render, interaction, long-task and memory budgets remain unmeasured.
- Historical version diff, opaque-version graph POST APIs and validated evidence IDs for architecture/tour steps need separately accepted API/read models.

UI-004 remains `in_progress`; these missing gates are not replaced by the passing component/build checks.
