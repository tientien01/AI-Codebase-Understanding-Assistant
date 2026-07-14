# Phase 3 — Canonical Code Intelligence

Status: Approved; INT-001 through INT-004 and a named deterministic graph/incremental CI smoke gate are verified, while production composition and real pipeline equivalence evidence remain open

## Outcome

One canonical adapter/IR/resolver/graph pipeline produces stable provenance-backed facts, declares language capabilities, and gives equivalent results for full and valid incremental builds.

## Tasks

`IDX-004` and `INT-001` through `INT-004`.

## Entry

Typed phase artifacts and atomic publish exist; representative multilingual fixtures are versioned.

## Exit gates

- Overlapping parser paths are consolidated or placed behind an explicit deprecated compatibility adapter.
- Stable entity identities and source-version locations are tested for edit/move/rename cases.
- Resolver outputs resolved, ambiguous, and unresolved diagnostics without LLM authority.
- Every graph edge has type, provenance, support class, version, and validation status.
- Generated language/capability matrix is evidence-backed.
- Full and incremental artifacts meet declared equivalence rules.

## Evidence

Golden parser suite, resolver accuracy report, graph validation report, capability report, and equivalence benchmark.

EVA-002 groups the existing graph-candidate/readiness and incremental-planner/equivalence suites into one named CI regression job. It changes no intelligence behavior and does not prove production parser/resolver/graph composition or full-versus-incremental equivalence on the real pipeline.
