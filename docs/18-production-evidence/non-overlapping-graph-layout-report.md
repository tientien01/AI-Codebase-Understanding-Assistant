# UI-016 Non-overlapping Graph Layout Report

Status: Verified local frontend implementation
Date: 2026-07-15

## Delivered behavior

- Dependencies, Request Flow and Call Flow now share deterministic parent-aware layered placement.
- Root positions remain stable during ordinary expansion; incoming and outgoing children occupy separate columns with a node-width-plus-gutter separation.
- Each column performs deterministic vertical collision resolution using node-height-plus-gutter spacing, including cached positions from earlier expansions.
- Canvas width grows with additional hop columns instead of clamping nodes against a fixed right or left boundary.
- Parallel and reverse-direction edges receive distinct lane offsets. Self-relations use a visible loop path rather than collapsing into a zero-length curve.
- Existing zoom, fit, node/edge selection, inspector and accessible relation-list behavior is retained.

## Validation

| Gate | Result |
| --- | --- |
| `npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx` | Pass — 19 tests |
| Dense layout fixture | Pass — 21 nodes, 9 callers, 11 callees, zero rectangle intersections |
| Multi-hop layout fixture | Pass — canvas grows beyond the former 1240px fixed width |
| `npm.cmd test -- --run` | Pass — 78 tests across 13 files |
| `npm.cmd run lint` | Pass |
| `npx.cmd tsc -b --pretty false` | Pass |
| `npm.cmd run build` | Pass — 145 modules transformed |
| Declared `git diff --check` | Pass; line-ending notices only |
