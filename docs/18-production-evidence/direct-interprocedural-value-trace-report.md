# Direct Interprocedural Value Trace Evidence

Task: `INT-006`
Date: 2026-07-16
Result: locally verified

## Delivered behavior

- Python DFG construction now emits stable call argument, call result and return boundary nodes.
- A `resolved-reference/v1` call with exactly one same-module target binds supported positional arguments to callee parameters through `dfg_argument_to_parameter`.
- Supported callee returns bind to the caller result through `dfg_return_to_call_result`; caller assignments retain `dfg_call_result_to_definition`.
- Cross-function edges carry call-site path/line, `static_resolved` resolution and `direct_interprocedural` scope metadata and remain labelled `inferred`.
- Ambiguous, unresolved, external and unsupported calls create no interprocedural value edge.
- Value Trace exposes the new semantic roles and relations, reports bounded direct-call support, and retains one-hop progressive expansion.

## Explicit limitations

- Python only; the current resolver confirms direct calls within one parsed module.
- Positional arguments only. The v1 IR does not retain keyword argument labels, so keyword binding is not guessed.
- Dynamic dispatch, imported cross-file targets, aliases, fields, mutation, taint, exceptions, generators and runtime behavior remain unsupported.
- Return bindings represent possible statically supported paths and do not assert which branch executes at runtime.
- Code Explorer semantic token replacement remains a separate task; existing text-token selection is unchanged.

## Verification

```text
backend\.venv\Scripts\python.exe -m pytest tests/test_code_analysis.py tests/test_graph_projection.py -q
40 passed

backend\.venv\Scripts\python.exe -m pytest tests/test_codebase_service.py -q
28 passed

npm.cmd test -- --run src/pages/workspace/GraphPage.test.tsx
26 passed

npm.cmd test -- --run
14 files passed, 92 tests passed

npm.cmd run lint
passed

npx.cmd tsc -b --pretty false
passed

npm.cmd run build
passed; 146 modules transformed
```

The focused regression matrix includes resolved argument/return binding, deterministic identities, inferred provenance, ambiguous/unresolved suppression, contextual seed matching, one-hop cross-function expansion and user-facing limitation language.
