# Graph Candidate Validation Report

Status: Verified local-profile contract evidence

Task: `INT-003`

Verified: 2026-07-13

## Delivered boundary

INT-003 adds strict immutable `graph-candidate/v1` records and a deterministic `normalized-graph/v1` artifact for resolved Python reference edges. Candidates carry repository/index ownership, canonical node/edge keys, one relation direction, controlled origin, producer/version, support type, SHA-256-bound source spans and the supporting reference key.

Normalization retains `accepted`, `changed` and `dropped` audit states plus stable bounded issue codes. Any critical issue makes active output empty. The compatibility emitter records candidates/issues and emits resolved import/call edges only from zero-critical active candidates.

## Validation matrix

| Area | Verified result |
| --- | --- |
| Valid pipeline | parser → resolver → candidates yields source symbol nodes and one accepted call edge with zero issues |
| Direction | `called_by` is reversed once to canonical `calls` and marked `changed/inverse_direction` |
| Duplicate | byte-equivalent canonical duplicate is dropped with `duplicate_candidate` warning |
| Dangling endpoint | critical `dangling_endpoint`, candidate dropped |
| Invalid semantics | critical relation, shape and canonical-key issues, candidates dropped |
| Provenance/ownership | missing span/producer and repository mismatch are critical |
| Inferred policy | below explicitly supplied synthetic confidence policy is critical; no global threshold is claimed |
| Canonical-key conflict | deterministic first semantic value plus critical conflicting-key audit; no active output |
| Determinism | reordered candidate input produces byte-equivalent normalized artifact output |

The invalid matrix produced the expected seven required failure families and **8 critical issues** because the deliberately malformed node violates both shape and canonical-key invariants. The valid pipeline produced **0 critical issues**.

## Verification results

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/intelligence/test_graph_candidates.py -q` | Pass: 4 tests in 0.35 s |
| `backend\.venv\Scripts\python.exe -m pytest tests/intelligence tests/test_code_analysis.py -q` | Pass: 38 tests in 0.57 s |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | Pass: 141 tests, 29 skipped in 77.56 s; 2 existing dependency/duplicate-ZIP warnings |
| `git diff --check` | Pass |

The skipped tests require the declared PostgreSQL/Redis integration profile and are unaffected by this in-memory candidate task.

## Evidence boundary and remaining gap

This evidence covers reference-derived Python file/symbol candidates and `imports`/`calls` edges only. It does not prove CFG/DFG candidate conversion, non-Python/framework producers, database persistence, replacement of the global legacy graph normalizer, query/projection limits, capability readiness, production worker composition or full/incremental production-output equivalence.
