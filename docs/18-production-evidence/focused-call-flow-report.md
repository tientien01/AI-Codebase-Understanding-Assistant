# UI-015 Focused Call Flow Explorer Report

Status: Verified local backend/frontend implementation
Date: 2026-07-15

## Delivered behavior

- Call Flow now opens with deterministic evidence-ranked function/method starting points rather than an arbitrary repository-wide node slice.
- Selecting a callable requests one bounded hop and presents incoming callers to the left and outgoing callees to the right while retaining complete visible relations.
- Calls, Called by and Both replace graph-direction jargon. Clicking a node only selects it; Continue from here expands one hop; Focus here intentionally resets around the new callable.
- Technical `call_site` and CFG nodes no longer consume the default Call Flow canvas. Direct resolved calls and existing built-in, standard-library, framework, external and unresolved classifications remain distinguishable.
- Callable summaries report indexed resolved/external/unresolved counts and direct-recursion signals. The inspector reports visible fan-in/fan-out and visible cycles without global quality or dead-code claims.
- Keyboard-selectable edges and the accessible relation list open a relation inspector with caller, target, available source locator/expression, resolution label, support, provenance and index version.
- Limited and empty wording states that missing static support does not prove a runtime call is absent. Numeric confidence is not presented as a calibrated probability.

## Validation

| Gate | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest ..\tests\test_graph_projection.py -q` | Pass — 16 tests, one third-party deprecation warning |
| `npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx` | Pass — 18 tests |
| `npm.cmd test -- --run` | Pass — 77 tests across 13 files |
| `npm.cmd run lint` | Pass |
| `npx.cmd tsc -b --pretty false` | Pass |
| `npm.cmd run build` | Pass — 145 modules transformed |
| Declared `git diff --check` | Pass; line-ending notices only |

## Remaining evidence boundaries

- The current resolver does not provide a production contract for multiple possible dynamic-dispatch targets, so the UI does not invent candidates or candidate probabilities.
- Source expression and exact call-site location appear only when existing edge metadata supplies them; otherwise the inspector uses the caller source range and says the detailed locator was not reported.
- Recursion beyond a direct self-call is identified only within the currently visible bounded projection. No global recursive-group total is claimed.
- Call Flow is static index evidence, not observed runtime execution, timing, branch order, production-use or dead-code proof.
