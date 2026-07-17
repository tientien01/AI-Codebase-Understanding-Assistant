# Phase 4 — Retrieval and Evidence

Status: Approved; RET-001 through RET-004 and the EVA-001 deterministic evaluation foundation are verified, while production-scale thresholds, load qualification and release evidence remain incomplete

## Outcome

Queries use measurable typed retrieval and ranking, and only validated repository/version-bound support becomes evidence or prompt context.

## Tasks

`RET-001` through `RET-004` and `EVA-001` foundation work.

## Entry

Stable entities, graph provenance, capability readiness, and benchmark fixtures exist.

## Exit gates

- Exact, lexical, metadata, graph, and optional semantic retrievers share typed inputs/outputs.
- Ranking configuration, normalization/fusion, filters, and index compatibility are versioned.
- Evidence selector enforces boundary, source existence, range, security, freshness, and support type.
- Context builder produces an inspectable repository digest within a token budget.
- Keyword, naive vector, and hybrid methods run on the same versioned dataset.
- Accepted retrieval, citation, latency, and cost thresholds pass.

## Evidence

Reproducible evaluation run, ranking regression, evidence validation suite, context-budget report, and load results.

`RET-001` supplies the shared typed request/candidate boundary, deterministic classifier, compatibility regression and insufficient-evidence negatives. It does not satisfy the remaining ranking configuration, fusion, evidence selection, evaluation dataset, threshold or load gates.

`RET-002` adds content-addressed rank-only weighted RRF, explicit retriever/filter/limit/dedup/tie policy and deterministic ranking regression. It does not satisfy evidence selection/context budgeting, evaluation dataset, learned-ranker adoption, accepted threshold or load gates.

`RET-003` validates current owned source/hash/range/security/support before promotion, creates content-bound deterministic evidence IDs, selects diverse whole spans within an inspectable token budget, and preserves explicit limited/insufficient outcomes. It does not satisfy claim-level support validation, versioned evaluation datasets, accepted quality/latency thresholds or load gates.

`EVA-001` adds a content-addressed six-case retrieval dataset, reviewed exact/keyword, deterministic semantic-fixture and hybrid baselines, metric formulas, negative/ambiguous coverage and a reproducible checksummed runner. It does not claim real embedding/provider quality, answer correctness, production latency/load, accepted numeric thresholds or CI release blocking; those remain later evaluation/release work.

`RET-004` runs three real local `embeddinggemma` repetitions over those exact
candidate inputs. The versioned sparse+dense hybrid improves macro Recall@3 from
0.6667 to 1.0 and reciprocal rank from 0.8 to 0.9 without reducing the measured
insufficient-evidence accuracy. Query p95 is 334.5 ms, maximum corpus embedding time
is 1.37 s and observed model memory is 680,379,023 bytes on the recorded Windows
capacity profile. The reviewed benchmark policy accepts RET-005 prototyping; this is
not a production-scale load, answer-quality or release-threshold qualification.
