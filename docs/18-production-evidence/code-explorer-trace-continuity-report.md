# Code Explorer and Value Trace Continuity Evidence

Task: `UI-022`
Verified: 2026-07-16

## Delivered behavior

- Repository folders are keyboard-operable tree items with persistent expand/collapse state, `Collapse all`, and `Reveal active` controls.
- Search reveals matching descendant paths without overwriting the unfiltered expansion state.
- Tree scroll is stored per repository for the browser session. Selecting another file retains the mounted tree and the previous source while the new file is visibly loading.
- The canonical Code route owns the selected repository-relative file, line, and optional validated `value-context:v1` trace. Per-file source scroll is transient repository-scoped session state.
- Selecting a source identifier opens the existing bounded progressive Value Trace below the code without narrowing the source reader. The panel is vertically resizable, collapses to a compact value/relation summary, and supports close, full-graph, graph expansion, source opening, and return-to-source without losing the trace context.
- Selected-value and relation details render after the embedded graph instead of absolutely covering it. Their close actions remain independent from closing the whole trace.
- Closing the source identifier chooser clears both local selection and the canonical `line` query while retaining an active trace context when present, so the chooser cannot immediately reappear.
- Workspace navigation remembers the last canonical Code URL for each repository, so Code/Graph switching returns to the same file, line, and trace.

## State and security ownership

- React Router owns shareable file, line, and trace context.
- TanStack Query owns file and graph server state; `keepPreviousData` prevents a page-level replacement during file transitions.
- Session storage owns only repository-scoped expansion and scroll state plus the last repository-relative Code URL. No host path is stored.
- Malformed trace payloads are decoded defensively and fail closed to normal Code Explorer behavior.
- Graph projection limits, deterministic evidence, one-hop expansion, coverage, and limitation language remain server-owned and unchanged.

## Known limits

- This is a static indexed value flow, not a runtime debugger or runtime value recorder.
- Source editing, Monaco integration, unsaved buffers, cross-window synchronization, and database persistence remain out of scope.
- The tree is not virtualized; a measured size breach still requires the existing performance-contract follow-up.
- The user-selected embedded panel height is transient CSS resize state and is not persisted across reloads.

## Verification

Executed from `frontend` unless noted:

| Gate | Result |
| --- | --- |
| Focused UI-022 Vitest suite | Passed: 6 files, 74 tests |
| Full Vitest suite | Passed: 16 files, 110 tests |
| `npm.cmd run lint` | Passed |
| `npx.cmd tsc -b --pretty false` | Passed |
| `npm.cmd run build` | Passed; 147 modules transformed, existing bundle-size warning only |
| Scoped `git diff --check` | Passed; line-ending notices only |

The focused regressions cover folder collapse/persistence, transient search expansion, tree scroll restoration, source-line routing and clearing, bottom-panel collapse, in-flow inspector dismissal, embedded trace actions, full-graph source return, canonical trace validation, and last-Code-location navigation.
