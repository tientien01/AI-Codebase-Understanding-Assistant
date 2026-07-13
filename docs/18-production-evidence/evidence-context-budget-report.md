# RET-003 Evidence Context Budget Report

Status: Verified task evidence; not release qualification
Task: `RET-003`
Verified: 2026-07-13
Environment: local Windows Python 3.11 profile

## Outcome

Ranked candidates now pass through a deterministic validation and selection boundary before evidence persistence. Promotion verifies repository/index ownership and freshness, indexed canonical source identity, raw source SHA-256, inclusive line range, skipped/security-blocked path policy, chunk hash and controlled support type. Valid spans receive opaque `evidence_` identities bound to repository, index, source, hashes and range; repeated persistence is idempotent.

The context records repository/index/ranking identities, ordered whole evidence blocks, per-block estimates, exact used/budget totals, selected candidate IDs, stable rejection reasons, omission counts, status, budget truncation reason and missing requirements. The declared estimator is `24 + ceil(characters / 4)` tokens per block. Selection first applies question coverage, named-target, support and ranked priorities, then source diversity; it never truncates inside a span.

The compatibility agent now consumes ranked results through this context boundary and persists citations only for selected validated blocks. Public API schemas and direct search compatibility remain unchanged.

## Verification

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/evidence/test_evidence_context.py -q` | 14 passed |
| `backend\.venv\Scripts\python.exe -m pytest tests/evidence tests/retrieval tests/test_codebase_service.py tests/test_service_boundaries.py -q` | 80 passed; 1 existing duplicate-ZIP warning and 1 dependency deprecation warning |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | 200 passed, 29 skipped; 1 existing duplicate-ZIP warning and 1 dependency deprecation warning |
| `git diff --check` | Recorded after documentation closure |

The regression covers stable selection and persistence, source/hash/range/blocked rejection, stale and cross-owner failure, input-order invariance, source diversity, exact token totals, oversized blocks, partial budgets, multi-step undercoverage, invalid policy and compatibility-workflow projection.

## Limitations

- Token estimates use the declared deterministic character estimator, not a provider tokenizer.
- The repository compatibility state retains skipped-file policy directly; security-warning records are consumed when a repository state supplies them, but production ingestion-to-index security artifact composition remains separate work.
- The selector validates candidate support provenance but does not extract claims or judge claim-to-evidence entailment.
- Historical index selection, multi-round repair, persistent structured traces, versioned evaluation datasets, accepted thresholds and load qualification remain outside `RET-003`.
- This report is task evidence, not Phase 4 exit or production release qualification.
