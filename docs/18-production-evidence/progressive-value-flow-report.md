# UI-018 Progressive Value Flow Evidence

Status: Verified locally
Task: `UI-018`
Verified: 2026-07-15
Profile: Windows local development profile; no dependency or schema changes

## Delivered outcome

Value Flow now opens as a dedicated root-first intraprocedural DFG explorer rather than the generic broad graph page. The initial response contains deterministic, searchable parameter, definition and use candidates without relations. Selecting a stable indexed value requests one bounded hop and supports the user-facing `Comes from`, `Flows to` and `Both` modes.

The backend keeps stored `dfg_node` and `dfg_*` truth unchanged. The UI presents semantic roles and readable relation verbs, retains source/support/provenance/index evidence, lays origins to the left and uses to the right, and preserves canvas panning, node dragging and the keyboard-accessible relation list.

## Projection evidence

- Seed strategy: `value-starting-points/v1`.
- Stable ranking uses stored role, direct DFG degree, source path, source line and opaque node ID.
- Seed coverage reports indexed values, parameters, definitions, uses and supported relations.
- Neighbor mode forces depth one and uses existing server node/edge budgets, direction traversal, continuation metadata and no-dangling-edge behavior.
- Empty and limited language explicitly states that missing static relations do not prove missing runtime behavior.

## Verification

| Gate | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests\test_graph_projection.py -q` via the task working-directory equivalent | Passed: 18 tests, 1 existing OpenTelemetry dependency warning |
| `npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx` | Passed: 22 tests in 1 file |
| `npm.cmd test -- --run` | Passed: 82 tests across 14 files |
| `npm.cmd run lint` | Passed with 0 errors |
| `npx.cmd tsc -b --pretty false` | Passed |
| `npm.cmd run build` | Passed: Vite 8.1.0, 145 modules transformed; JS 487.80 kB / 138.29 kB gzip; CSS 84.93 kB / 17.87 kB gzip |
| Declared `git diff --check` scope | Passed; Git emitted Windows CRLF conversion warnings only |

Focused backend tests prove deterministic seed ordering under reversed inputs, semantic counts, explicit partial scope, one-hop bounding and incoming/bidirectional traversal. Focused frontend tests prove the root-first browser, semantic roles, user-facing traversal language, one-step expansion, relation evidence inspection and direction reprojection.

## Explicit limitations and non-claims

The compatibility DFG producer currently supports only intraprocedural parameter, definition and use nodes with inferred static relations. UI-018 does not claim or synthesize:

- independent return-value or call-result nodes;
- expression transformation chains;
- mutation, alias or field read/write tracking;
- inferred types;
- caller-argument to callee-parameter or callee-return binding;
- source, sanitizer, sink or vulnerability classification;
- runtime execution, use or completeness.

Those capabilities require separately authorized analyzer tasks and evidence before the UI may present them.
