# RET-002 Ranking Regression Report

Status: Verified task evidence; not release qualification
Task: `RET-002`
Verified: 2026-07-13
Environment: local Windows Python 3.11 profile

## Outcome

Typed retrieval candidates now pass through immutable `ranking-config/v1`. The default canonical configuration identity is `rankcfg_277eb94cb50ff8583271fba2`; it records every controlled retriever, enabled state, per-retriever candidate limit and weight, rank-only normalization, reciprocal-rank fusion with `rrf_k=60`, allowed support filters, repository/index/entity/source/span deduplication, no diversity transform, final limit 20, context-budget metadata 8000 and no undeclared reason boosts.

Ranking validates repository/index ownership, applies retriever/support/per-source limits before fusion, merges duplicate source-span contributions, and computes `sum(weight / (rrf_k + rank))`. The compatibility score is bounded against the theoretical rank-one maximum; final ties use fused score, support strength, best rank, canonical entity key and stable candidate ID. Raw scores are retained for diagnostics but are never added across retrievers.

## Verification

| Command | Result |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest tests/retrieval/test_ranking.py -q` | 18 passed |
| `backend\.venv\Scripts\python.exe -m pytest tests/retrieval tests/test_service_boundaries.py tests/test_code_analysis.py -q` | 61 passed; 1 dependency deprecation warning |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | 186 passed, 29 skipped; 1 existing duplicate-ZIP warning and 1 dependency deprecation warning |
| `git diff --check` | Recorded after documentation closure |

The regression matrix includes hand-computed RRF, canonical identity changes, invalid configuration, ownership/support/retriever/limit filters, source-span deduplication and contribution merging, deterministic ties, final bounds, input-order/raw-score-scale invariance, explicit boost behavior, and the inherited blank/unrelated insufficient-evidence cases.

## Limitations

- The default equal weights and operational limits are a transparent deterministic baseline, not accepted quality/latency thresholds.
- Configuration is immutable/content-addressed in process but is not yet persisted or exposed through an API/settings surface.
- No learned reranker is adopted; future adoption requires a versioned evaluation improvement over this baseline.
- Context-budget value is recorded only. Evidence eligibility, selection and actual context construction/truncation belong to `RET-003`.
- This report is not the versioned evaluation dataset, multi-run threshold acceptance, load evidence or release qualification required by later tasks.
