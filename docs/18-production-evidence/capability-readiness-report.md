# Capability Readiness Invariant Report

Status: Verified local-profile contract evidence

Task: `INT-004`

Verified: 2026-07-13

## Delivered boundary

INT-004 adds a strict deterministic calculator that consumes declared capability specifications and validated evidence only. It emits the existing accepted `CapabilityReadiness` records, a `capability-readiness/v1` report, mandatory capability list, activation summary and manifest-compatible state/coverage projection.

Inputs cover required artifact state, measured processing coverage, unresolved references, critical validation issue IDs, source freshness, declared support, optional provider availability and capability dependencies. The calculator performs no filesystem/database/network/provider/LLM access and uses no hidden numeric pass threshold.

## Invariant matrix

| Input condition | Verified state/behavior |
| --- | --- |
| Complete validated evidence | `ready` |
| Partial file coverage | `limited` with measured successful/failed counts and fraction |
| Unresolved references | `limited`; count is disclosed and does not alone block a mandatory capability |
| Complete profile processing failure | `failed` |
| Required artifact missing/failed/stale | `unavailable` / `failed` / `stale` for that capability only |
| Critical validation issue | `failed`, linked to the stable issue ID |
| Unsupported/no eligible input | `unavailable` |
| Optional provider unavailable | dependent optional capability `unavailable`; unrelated core state unchanged |
| Dependency limited | dependent capability `limited` |
| Dependency failed/unavailable/stale | dependent capability cannot become ready |
| Mandatory summary | activation allowed only when every mandatory state is `ready` or `limited` |
| Invalid spec/evidence/dependency graph | duplicate, mismatch, unknown dependency and cycle fail closed |
| Reordered input | byte-equivalent report output |

All five accepted runtime states are exercised. Forbidden pseudo-states such as `building`, `not_started`, `in_development`, or `ready_with_warnings` are not representable in output.

## Verification results

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/intelligence/test_capability_readiness.py -q` | Pass: 11 tests in 0.15 s |
| `backend\.venv\Scripts\python.exe -m pytest tests/intelligence tests/indexing/test_validation_activation.py -q` | Pass: 37 tests, 5 skipped in 0.43 s |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | Pass: 152 tests, 29 skipped in 76.64 s; 2 existing dependency/duplicate-ZIP warnings |
| `git diff --check` | Pass |

The skipped tests require the declared PostgreSQL/Redis integration profile. INT-004 changes no persistence or activation code.

## Evidence boundary and remaining gap

This evidence proves readiness calculation invariants from declared inputs. It does not prove that the production worker composes parser/resolver/graph/retrieval artifacts into these inputs, persists/publishes the records, achieves full/incremental readiness equivalence, or passes release gates. Phase 3 production composition evidence remains open while RET-001 incremental delivery may begin.
