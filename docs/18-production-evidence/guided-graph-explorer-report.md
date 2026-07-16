# UI-010 Guided Graph Explorer Report

Status: Verified local frontend implementation
Date: 2026-07-15

## Delivered behavior

- Graph Explorer now opens with a relationship-question chooser instead of duplicating the architecture summary owned by Overview.
- Dependencies explains file/module nodes and `imports` direction; Request Flow explains endpoint/callable nodes and returned API/call relations; Call Flow limits its default projection to callable nodes and call relations; Value Flow is clearly marked as advanced compiler-level analysis.
- Every detail view states its user question, node meaning, arrow meaning, current direction, depth, focus and bounded included counts.
- Human-readable focus selectors replace the canonical root-key text input while still sending canonical node IDs to the existing projection contract.
- Switching relationship views clears an incompatible root from the prior projection while preserving the selected depth.
- Nodes remain fully visible until explicit selection. Selecting a node highlights direct neighbors without removing graph content, and selection can be cleared.
- A no-edge result explains valid leaf, unresolved static-analysis and limited-projection possibilities instead of leaving an ambiguous canvas.
- Projection filters are compacted behind a Filters disclosure; the selected-entity inspector is sticky; relation types are visible above the canvas.
- The complete keyboard and screen-reader relation alternative remains available but is collapsed by default and follows the dark workspace theme.
- No backend route, schema, graph fact, dependency or package lock changed.

## Validation

| Gate | Result |
| --- | --- |
| `npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx` | Pass — 7 tests |
| `npm.cmd test -- --run` | Pass — 66 tests across 13 files |
| `npm.cmd run lint` | Pass |
| `npx.cmd tsc -b --pretty false` | Pass |
| `npm.cmd run build` | Pass — 145 modules transformed |
| `git diff --check -- frontend docs` | Pass |

CI was intentionally not checked at the project owner's request.
