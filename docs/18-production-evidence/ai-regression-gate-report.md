# EVA-002 AI, Graph, and Incremental Regression Gate Report

Status: Verified local clean-environment and GitHub-hosted named smoke gate

Task: `EVA-002`

Verified locally: 2026-07-14

## Outcome

EVA-002 adds a named GitHub Actions job, `AI, graph, and incremental regression`, which installs the locked Python 3.11 environment, runs the existing evaluation, graph provenance/readiness, incremental planning/equivalence and assistant suites, produces the frozen EVA-001 run, and applies one `evaluation-gate/v1` policy.

The policy is explicitly classified `ci_regression_only`. It detects changes to the reviewed synthetic baseline and cannot approve production quality, providers, performance, cost, security or release readiness.

## Frozen identities

- Gate configuration: `evalgate_72f1a29cb6021ce458f0723b`
- Dataset revision: `sha256:734b850ed37fcc2a7fa5aaf6f6903c2c1cbc3a5b85db68ecfa1cc024546ecc49`
- Fixture revision: `sha256:535617ad5e9d94d55d1f4a627498e84f72a8caa0a9f87934962884a55e6b03c9`
- Raw results: `sha256:b409aa0645512ee22af4248f955b2eb3428aa898509f613d723872a178cd57c4`
- Local smoke decision: `sha256:2ffa722be4cd0b643cfa59673d41bcbf7d90572b364771b613220f8fdb5c9966`
- Methods: `rankcfg_d7249196cbee0a6a0b130538`, `evalcfg_bb8f81775800d8edd8d954d5`, `rankcfg_277eb94cb50ff8583271fba2`

## Reviewed smoke rules

| Rule | Comparison |
| --- | --- |
| Exact/keyword Recall@3 | `>= 0.666666666667` |
| Naive semantic-fixture Recall@3 | `>= 0.4` |
| Naive semantic-fixture insufficient-evidence accuracy | `>= 1.0` |
| Deterministic hybrid Recall@3 | `>= 1.0` |
| Deterministic hybrid nDCG@3 | `>= 0.926185950714` |
| Deterministic hybrid duplicate rate | `<= 0.0` |

Policy loading rejects unsupported classification/schema, unknown or duplicate rules, non-finite bounds and incomplete method identities. Run evaluation additionally checks dataset/fixture/provider/capacity/raw-result/method identities, recomputes raw-result integrity, requires completed non-errored cases and fails on missing, undefined, non-finite or regressed metrics. Diagnostics are deterministically ordered and contain scalar values only.

## Local verification

```powershell
$env:PYTHONPATH = "backend"
& backend\.venv-clean\Scripts\python.exe -m pytest tests/evaluation/test_gates.py -q
# 13 passed

& backend\.venv-clean\Scripts\python.exe -m pytest tests/evaluation tests/intelligence/test_graph_candidates.py tests/intelligence/test_capability_readiness.py tests/indexing/test_incremental_planner.py tests/indexing/test_equivalence_service.py tests/assistant -q
# 93 passed

& backend\.venv-clean\Scripts\python.exe -m pytest tests -q
# 260 passed, 29 skipped, 2 existing warnings

& backend\.venv-clean\Scripts\python.exe -m app.services.evaluation.runner --dataset evaluation/datasets/retrieval-v1 --output .tmp/eva-002-run.json --code-revision EVA-002-ci-smoke --index-version idx_eva_002_ci --started-at 2026-07-14T00:00:00Z --completed-at 2026-07-14T00:00:00Z
& backend\.venv-clean\Scripts\python.exe -m app.services.evaluation.gates --config evaluation/gates/eva-002-ci.json --run .tmp/eva-002-run.json --output .tmp/eva-002-gate.json
# EVA-002 gate PASSED: evalgate_72f1a29cb6021ce458f0723b
```

The 29 skips are the existing PostgreSQL/Redis integration profile. EVA-002 changes no database, broker or runtime domain path.

## Remote CI status

Stacked draft PR: [#27](https://github.com/tientien01/AI-Codebase-Understanding-Assistant/pull/27), targeting `agent/eva-001-evaluation-runner` while EVA-001 PR #26 remains open.

The named `AI, graph, and incremental regression` job passed for commit `2aba763` in both observed triggers:

- [push-triggered job](https://github.com/tientien01/AI-Codebase-Understanding-Assistant/actions/runs/29305775100/job/86998678090): passed in 17 seconds.
- [pull-request-triggered job](https://github.com/tientien01/AI-Codebase-Understanding-Assistant/actions/runs/29305796035/job/86998735645): passed in 13 seconds.

Frontend checks and the first backend run also passed at the observation time; the duplicate pull-request backend job was still running and is not claimed as complete evidence here. EVA-002 acceptance is owned by the named smoke job plus the clean local full regression above.

## Limitations

- The smoke floors describe six synthetic cases and are not statistically accepted thresholds.
- No real embedding, vector store, reranker, LLM/provider, manual answer judge, load, latency, cost or security run is included.
- Graph and incremental suites cover their current deterministic component boundaries; production worker/parser/resolver/graph composition remains open.
- Release qualification still requires immutable candidate evidence and owner acceptance under the evaluation contract.
