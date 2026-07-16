# UI-021 Contextual Value Trace Evidence

Status: Verified locally
Task: `UI-021`
Verified: 2026-07-15

## Delivered outcome

- Value Flow was removed from every primary relationship tab and the global question chooser. The `data-flow` route and deterministic DFG engine remain available for contextual deep links.
- Code Explorer now lets keyboard or pointer users select a source line and choose one extracted identifier to trace. The request contains only repository-relative file, line and identifier context.
- Selected Request Flow endpoints and Call Flow callables expose scope-level trace actions using their indexed source ranges.
- Compact versioned context selectors travel through the existing graph `root` contract. The server decodes them without filesystem access and matches only indexed DFG nodes by exact file/line/value or bounded file/range.
- A context-free Value Trace renders guidance instead of repository-wide seeds. A matched context renders only deterministic candidates, then preserves Comes from / Flows to / Both, one-hop expansion, evidence inspectors, relation fallback, canvas pan and node drag.
- Empty matches and expanded results retain explicit intraprocedural/static limitations; no runtime, cross-function, transformation or taint relation is synthesized.

## Verification

| Gate | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/test_graph_projection.py -q` | Passed: 19 tests; 1 dependency warning |
| `backend\.venv\Scripts\python.exe -m pytest tests/test_codebase_service.py -q` | Passed: 28 tests; 2 pre-existing warnings |
| `npm.cmd test -- --run src/pages/workspace/CodeExplorerPage.test.tsx src/pages/workspace/GraphPage.test.tsx` | Passed: 27 tests across 2 files |
| `npm.cmd test -- --run` | Passed: 91 tests across 14 files |
| `npm.cmd run lint` | Passed with 0 errors |
| `npx.cmd tsc -b --pretty false` | Passed |
| `npm.cmd run build` | Passed: Vite 8.1.0, 146 modules; JS 490.59 kB / 139.92 kB gzip; CSS 86.11 kB / 18.11 kB gzip |
| Declared `git diff --check` scope | Passed; Git emitted Windows CRLF conversion warnings only |

## Remaining analyzer limitations

The compatibility DFG remains intraprocedural. A scope action finds indexed values inside the selected source range but does not bind caller arguments to callee parameters. Token matching is exact against the indexed DFG value label at the selected line. Missing context matches or edges remain unknown runtime behavior, not proof of absence.
