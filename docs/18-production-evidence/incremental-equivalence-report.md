# Incremental Planning and Equivalence Report

Status: Verified synthetic contract evidence

Task: `IDX-004`

Verified: 2026-07-13

## Delivered boundary

IDX-004 adds two unused internal production boundaries:

- a strict immutable affected-set planner that compares complete component/configuration identities, classifies fingerprint dimensions and exact unique-content moves, follows declared typed reverse dependencies, and emits stable full-build fallback reasons when safe reuse cannot be established;
- an exact canonical comparator for facts, references, graph nodes, graph edges, chunks, lexical state, readiness, fingerprints, and benchmark answers, with bounded deterministic digest-only diagnostics.

No repository content, source payload, database, artifact store, provider, current indexer, parser, graph builder, or worker is read or changed by these boundaries.

## Fixture and failure matrix

| Area | Verified cases |
| --- | --- |
| Change classification | add, delete, raw/normalized content, documentation, structure, public API/signature, dependency, unchanged reuse |
| Move handling | exact unique-content move/rename candidate; ambiguous duplicate-content move forces full |
| Compatibility | producer, schema, rule, security-policy, ranking, and normalized-configuration identity changes force full |
| Dependency expansion | typed reverse direct/transitive dependents; stable input-order-independent plan bytes |
| Safety budgets | affected-node, dependency-depth, and repository-fraction limits force full with stable reason codes |
| Invalid input | duplicate snapshot identities, non-canonical paths/keys, duplicate edges, and unknown endpoints reject reuse |
| Equivalence | canonical declaration-order independence; exact comparison of all nine mandatory families |
| Diagnostics | missing-on-either-side and digest mismatch results are stable, bounded, and disclose no source payload |

The numeric limits in tests are synthetic enforcement fixtures, not claimed universal production thresholds.

## Verification results

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/indexing/test_incremental_planner.py tests/indexing/test_equivalence_service.py -q` | Pass: 18 tests in 0.18 s |
| `backend\.venv\Scripts\python.exe -m pytest tests/indexing -q` | Pass: 33 tests, 5 skipped in 0.75 s |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | Pass: 121 tests, 29 skipped in 60.51 s; 2 existing dependency/duplicate-ZIP warnings |
| `git diff --check` | Pass |

Skipped tests require the declared PostgreSQL/Redis integration profile and are unchanged by IDX-004. This task's new tests require neither service.

## Evidence boundary and remaining gap

This report proves deterministic metadata planning, safe fallback, and exact canonical snapshot comparison on synthetic fixtures. It does **not** prove that the current parser, resolver, graph, chunking, lexical, readiness, or benchmark pipeline produces equivalent full and incremental outputs. Those producers are intentionally outside IDX-004 and must later populate this harness with representative versioned fixtures after the `INT-*` consolidation tasks and production-worker composition are authorized.

Phase 2 production-worker composition therefore remains open, and Phase 3 must not claim production-output equivalence from this report alone.
