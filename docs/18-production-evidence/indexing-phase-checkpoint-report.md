# IDX-002 Typed Indexing Phase and Checkpoint Evidence

Status: Passed

Verified: 2026-07-13

Task: `IDX-002`

## Delivered boundary

- Added the canonical production-v1 pre-activation phase order and strict immutable phase input/output models.
- Added explicit resource bounds, deterministic idempotency identities, progress/cancellation boundaries, and transient/permanent failure classification.
- Added deterministic `phase-checkpoint/v1` envelopes stored through the IDX-001 immutable artifact port.
- Added declared-input execution and longest-valid-prefix resume without scanning storage for undeclared state.
- Added checksum, size, ownership, phase-version, configuration, input-identity, output-schema, and contiguous-order validation before skipping work.

This internal boundary is intentionally not wired into the production worker yet. No database, worker, lease, API, local indexing implementation, activation, dependency, or frontend behavior changed.

## Verification profile

- Project virtual environment: `backend/.venv`
- Artifact backend: isolated `tmp_path` filesystem roots
- Fixtures: deterministic synthetic bytes and in-process phase doubles
- Full regression: local profile; production PostgreSQL/Redis URLs intentionally absent, so their existing integration tests skipped

## Commands and results

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/indexing -q
# 9 passed in 0.50s

backend\.venv\Scripts\python.exe -m pytest tests/artifacts -q
# 18 passed in 0.26s

backend\.venv\Scripts\python.exe -m pytest tests -q
# 97 passed, 24 skipped, 2 known warnings in 34.75s

git diff --check
# Passed with no output
```

The two warnings are the existing duplicate-ZIP fixture warning and an OpenTelemetry dependency deprecation warning. The skipped cases require production integration URLs and are not declared gates for IDX-002.

## Verified invariants

- The registry rejects missing, duplicate, or reordered canonical phases and invalid artifact declarations.
- Resource limits are positive and immutable; schema, ownership, key scope, and checksum identities are strict.
- Equal inputs/configuration/component versions produce equal idempotency keys; any identity change changes the key.
- A retry with a complete compatible checkpoint set executes no phase again.
- Missing, out-of-order, incompatible, corrupt-checkpoint, or corrupt-output state stops resume at the first affected phase, regardless of later references.
- Phase exceptions are safely classified without leaking implementation details.
- Failure, cancellation, or undeclared output never publishes a completed checkpoint.

## Remaining work

IDX-003 owns validation semantics, production worker composition with fencing predicates, manifest finalization, and the atomic expected-previous-version activation transaction. IDX-002 does not activate or serve a candidate index.
