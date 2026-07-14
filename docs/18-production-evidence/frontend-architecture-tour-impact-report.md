# UI-004 Architecture, Tour, Graph, and Impact Evidence

Status: Local implementation and browser qualification verified; named CI gate pending

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

No API, database, graph fact, indexing, retrieval, storage or historical-version behavior changed. The locked frontend test toolchain adds `@playwright/test@1.61.1` and `@axe-core/playwright@4.12.1` only.

## Verification results

| Gate | Observed result |
| --- | --- |
| Clean dependency install | `npm.cmd ci` added 239 locked packages successfully |
| Targeted frontend | 14 passed across `GraphPage`, UI-004 workspace and application routing suites |
| Full frontend | 45 passed across 7 files |
| Lint | Passed with zero errors or warnings |
| TypeScript | `npx.cmd tsc -b --pretty false` passed |
| Production build | Passed; 131 transformed modules |
| Browser E2E | 6 passed: architecture/tour/source, graph focus/relation fallback/reduced motion, current impact disclosure, and three graph-size observations |
| Accessibility | axe WCAG 2 A/AA and 2.1 A/AA: zero serious or critical violations on Architecture/Code, Graph and Impact journeys |
| Lock review | Intentional exact additions only: Playwright 1.61.1 and axe-playwright 4.12.1 |
| Diff hygiene | `git diff --check -- frontend docs` passed locally |

## Graph and bundle observations

The existing maximum-projection component fixture still renders all 220 returned nodes and 219 returned relations. UI-004 additionally asserts one SVG edge per returned relation and preserves the full relation-list count after selection. These jsdom observations are regression evidence, not a browser interaction or memory threshold.

| Asset | UI-003 | UI-004 | Delta |
| --- | ---: | ---: | ---: |
| JS | 362.30 kB / 110.98 kB gzip | 374.30 kB / 114.36 kB gzip | +12.00 kB / +3.38 kB gzip |
| CSS | 25.18 kB / 6.08 kB gzip | 36.15 kB / 8.59 kB gzip | +10.97 kB / +2.51 kB gzip |
| Transformed modules | 131 | 131 | 0 |

The deterministic Chromium observations after a clean install were:

| Projection | Returned graph | Ready | Navigation | DOM elements |
| --- | ---: | ---: | ---: | ---: |
| Small | 12 nodes / 11 edges | 283 ms | 165 ms | 375 |
| Medium | 80 nodes / 79 edges | 321 ms | 172 ms | 1,055 |
| Large | 220 nodes / 219 edges | 372 ms | 169 ms | 2,315 |

Every returned node and edge was present before the observation completed. These are repeatable qualification observations, not an accepted product latency or memory budget. No accepted Phase 6 bundle/browser threshold exists, so no release pass/fail is inferred from these values.

## Remaining qualification step

- The named `Frontend UI-004 E2E and accessibility` GitHub Actions job must pass on the follow-up pull request before UI-004 is marked completed.

Historical version diff, opaque-version graph POST APIs and validated evidence IDs for architecture/tour steps still need separately accepted API/read models; they are disclosed product limits, not fabricated by UI-004. Phase 6 release qualification and UI-005 also remain separate work.
