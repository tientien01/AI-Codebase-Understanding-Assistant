# UI-017 Graph-first Interaction Workspace Report

Status: Verified local frontend implementation
Date: 2026-07-15

## Delivered behavior

- Workspace sidebar has a keyboard-accessible collapse/expand control, persists preference locally, becomes a 76px icon rail and retains navigation targets plus collapsed tooltips.
- Active progressive Graph pages remove the redundant large page heading, compact relationship navigation, controls, status and entry summaries, and allocate the remaining viewport height to the canvas.
- Every legacy and progressive graph viewport supports primary-pointer panning on empty canvas in both axes, with grab/grabbing feedback and an accessible interaction label.
- Every graph node supports pointer/touch dragging inside canvas bounds. Manual position overrides immediately rerender all connected SVG edge paths and minimap positions.
- A four-pixel drag threshold separates click from drag; completing a drag suppresses the following synthetic click, while the next normal click retains existing selection/expansion behavior.
- Zoom-aware movement keeps pointer distance consistent at different scales. Keyboard focus, zoom, Fit, inspectors, edge selection and relation-list alternatives remain available.

## Validation

| Gate | Result |
| --- | --- |
| Focused `GraphPage` + `AppShell` tests | Pass — 21 tests across 2 files |
| Canvas pan assertion | Pass — horizontal and vertical scroll offsets follow background drag |
| Node drag assertion | Pass — node coordinates and connected SVG path change; drag click is suppressed |
| Sidebar assertion | Pass — state, ARIA, route target, tooltip and local persistence |
| `npm.cmd test -- --run` | Pass — 80 tests across 14 files |
| `npm.cmd run lint` | Pass |
| `npx.cmd tsc -b --pretty false` | Pass |
| `npm.cmd run build` | Pass — 145 modules transformed |
| Declared `git diff --check` | Pass; line-ending notices only |
