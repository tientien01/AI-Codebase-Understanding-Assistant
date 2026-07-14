# EVA-001 Retrieval Evaluation Foundation Report

Status: Verified deterministic local foundation; not release-threshold evidence

Task: `EVA-001`

Verified: 2026-07-14

Environment: locked Python 3.11 `.venv-clean`, provider-free synthetic-small profile, concurrency 1, cache disabled

## Outcome

EVA-001 adds one immutable `evaluation-dataset/v1` manifest with six `evaluation-case/v1` cases covering exact, lexical, semantic, graph-path, negative and ambiguous retrieval. Every method receives the same candidate IDs for a case. The runner compares exact/keyword, naive semantic top-k and the existing deterministic hybrid RRF, then retains per-case results, method configuration IDs, aggregate metrics, frozen identities and checksums.

No fixture file is executed or imported. Dataset loading rejects path escape, missing/stale hashes, invalid ranges/content, duplicate IDs/ranks, non-finite scores, ownership-key mismatch and unsupported schema/category values before scoring.

## Frozen identities

- Dataset: `retrieval-v1`
- Dataset revision: `sha256:734b850ed37fcc2a7fa5aaf6f6903c2c1cbc3a5b85db68ecfa1cc024546ecc49`
- Fixture: `retrieval_benchmark_repo`
- Fixture revision: `sha256:535617ad5e9d94d55d1f4a627498e84f72a8caa0a9f87934962884a55e6b03c9`
- Raw results: `sha256:b409aa0645512ee22af4248f955b2eb3428aa898509f613d723872a178cd57c4`
- Semantic run: `sha256:6d7dafe828f7c683d041264d9ca0c6b54e70b670fa4561270275b47cfcc5db4a`
- Exported report: `sha256:79d60a58b30c48091c08c5278aefcfab1b6fbf3fa4d28ada0d9fb49d40f13a3d`

## Metric contract

- Recall@k is unique relevant entities retrieved divided by declared relevant entities; it is undefined for cases without relevant entities.
- Precision@k is relevant ranked entries divided by declared `k`; it is undefined without relevant entities.
- MRR uses the first relevant rank. Binary nDCG@k uses `1/log2(rank+1)` and an ideal list capped by `min(relevant, k)`.
- Exact-target rank is the first relevant rank or null. Source diversity is unique sources divided by returned entries. Duplicate rate is one minus unique owned source spans divided by returned entries.
- Insufficient-evidence accuracy is evaluated only where `should_answer=false`; an empty result is correct. Aggregates are macro means over defined values only. Values are rounded to 12 decimal places.

## Deterministic comparison

These are regression baselines, not accepted thresholds.

| Method | Recall@3 | Precision@3 | MRR@3 | nDCG@3 | Insufficient-evidence accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Exact/keyword | 0.666666666667 | 0.333333333333 | 0.8 | 0.693855745205 | 0.5 |
| Naive semantic fixture | 0.4 | 0.133333333333 | 0.4 | 0.4 | 1.0 |
| Deterministic hybrid | 1.0 | 0.533333333333 | 0.9 | 0.926185950714 | 0.5 |

The ambiguous case intentionally exposes that retrieval-only baselines return candidates without a sufficiency/refusal decision. The negative nonexistent case remains empty for every method.

## Verification

```powershell
$env:PYTHONPATH = "backend"
& backend\.venv-clean\Scripts\python.exe -m pytest tests/evaluation -q
# 19 passed

& backend\.venv-clean\Scripts\python.exe -m pytest tests/evaluation tests/retrieval tests/evidence tests/assistant -q
# 95 passed

& backend\.venv-clean\Scripts\python.exe -m pytest tests -q
# 247 passed, 29 skipped, 2 existing warnings

& backend\.venv-clean\Scripts\python.exe -m app.services.evaluation.runner --dataset evaluation/datasets/retrieval-v1 --output .tmp/eva-001-run.json --code-revision EVA-001-local --index-version idx_eva_001 --started-at 2026-07-14T00:00:00Z --completed-at 2026-07-14T00:00:00Z
# exit 0; identities and checksums match this report
```

The 29 skips are existing PostgreSQL/Redis integration-profile tests. EVA-001 introduces no database, broker, provider or public runtime path; its required integration gate is the retrieval/evidence/assistant compatibility suite above.

## Limitations and decision

- Semantic candidates are deterministic observations, not a real embedding or vector-store measurement.
- No LLM answer correctness, completeness, groundedness, citation relevance, token/cost or provider-degradation score is claimed.
- Timing is explicitly `not_measured`; production-like latency, load, capacity and variance evidence remains absent.
- Numeric release thresholds require at least three declared production-like runs and owner acceptance. EVA-001 neither proposes nor accepts them.
- CI blocking and combined graph/incremental/agent gates remain candidates for separately authorized `EVA-002`.

Decision: the versioned dataset, baseline comparison and reproducible runner foundation pass EVA-001. This report does not advance the project to production-ready status.
