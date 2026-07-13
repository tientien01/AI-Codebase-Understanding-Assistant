# Phase 0 — Verified Baseline and Governance

Status: In progress

## Outcome

The project can be installed, inspected, tested, and planned reproducibly. Target specifications are separated from verified implementation, and every change starts from a scoped task.

## Scope and tasks

- `DOC-001`: executable production documentation.
- `DOC-002`: source/API/test/fixture/setup/capability verification.
- `DOC-003`: concrete identity/artifact, retrieval/trace/dataset, threat, telemetry/SLO, and UX interaction contracts.
- `FND-005`: establish targeted verification and clear the four-error frontend lint baseline that blocks the first green CI gate.
- Verify supported setup/test/build commands and dependency metadata gaps.
- Snapshot current API, schema, capabilities, fixtures, and known failures without changing behavior.

## Entry

Repository source and current tests are available; no production claim is assumed.

## Exit gates

- Documentation navigation, authority, roadmap, task template, and traceability are internally consistent.
- Development setup and baseline verification commands are recorded and reproducible.
- Current capability and gap reports cite source/tests rather than roadmap claims.
- Backend/frontend commands record both passing gates and known failures; imported repositories are excluded from safe test collection.
- The frontend lint prerequisite is complete and the first Phase 1 task is ready with exact paths, contracts, tests, and rollback.

## Evidence

Docs validation report, baseline test inventory, API/schema snapshot, source map, and approved next task.
