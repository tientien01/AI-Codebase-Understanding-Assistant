# Detailed Evaluation and Release-Regression Plan

Status: Accepted evaluation contract; release thresholds pending versioned evidence  
Authority: Evaluation cases, baselines, metrics, reproducibility, comparison, and threshold acceptance  
Owner: Evaluation and release owners  
Dependencies: `../runtime-and-dataset-contracts.md`, `../README.md`, `../../01-product/success-metrics.md`, evidence/assistant contracts  
Related source: `../../14-implementation-baseline/`  
Related tests: evaluation schema/runner, metric, reproducibility, provider degradation, and release regression suites  
Last verified: 2026-07-12

## Objective

Evaluation determines whether code intelligence, retrieval, evidence and bounded assistant behavior improve on simpler baselines without unjustified latency, cost, security or operational complexity. No semantic store, reranker, graph algorithm, model or workflow framework is adopted from intuition alone.

## Frozen run identity

Every run records dataset/case schema and revision, fixture ID/revision, code/release digest, repository/source snapshot and opaque index-version ID, parser/resolver/graph/chunker versions, ranking/workflow configuration IDs, provider/model/embedding/reranker identities, seed/temperature, security policy, capacity/environment profile, concurrency/cache condition, timestamps and budget configuration. Aggregate-only results cannot approve or block release without per-case outputs.

## Required baselines and methods

Run applicable methods on the same fixture/index/cases and comparable budgets:

1. Exact/keyword baseline: exact entity/path plus lexical results, no embeddings or agent.
2. Naive vector top-k: semantic top-k directly selected for context, no metadata/graph/sufficiency repair.
3. Deterministic hybrid: exact, lexical, metadata/document/config/test and bounded graph candidates with versioned fusion/evidence selection.
4. Hybrid plus optional semantic retrieval.
5. Optional reranker over an explicitly capped candidate set.
6. Bounded agentic workflow for cases whose typed deterministic workflow is insufficient.

Exact questions include an ablation assertion that planner, semantic search, reranker and provider are not called when exact deterministic evidence is sufficient.

## Evaluation case schema

Use `evaluation-case/v1` from `runtime-and-dataset-contracts.md`. Each case includes canonical expected entity keys, evidence spans/content hashes, relation paths, answer facts, acceptable alternatives, forbidden claims, `should_answer`, required source/support types, capability preconditions and budgets. Free-text expected summaries alone are insufficient ground truth.

Required case families:

- positive exact, lexical, semantic and graph-path questions;
- negative/nonexistent and unsupported claims;
- ambiguous entity and multiple-valid-answer cases;
- stale evidence and changed/moved source;
- unsupported or partially supported language profile;
- incomplete graph and excessive unresolved references;
- provider/vector/reranker outage and timeout;
- source prompt injection and secret-like content;
- graph/context/budget truncation;
- large repository/capacity class and concurrent queries;
- full versus incremental equivalence;
- cross-repository authorization denial;
- deterministic result with optional providers disabled.

Dataset size is proposed by an evaluation task from statistical/coverage needs; this contract does not invent a universal “questions per category” threshold.

## Metrics

| Domain | Required metrics |
| --- | --- |
| Retrieval | Recall@k, Precision@k, MRR, nDCG, exact-target rank, source diversity, duplicate rate |
| Evidence | eligibility/source/range/hash validity, selection coverage, citation syntactic validity, citation relevance |
| Claims/answers | claim support, correctness, completeness, groundedness, unsupported-claim/hallucination rate, insufficient-evidence accuracy |
| Graph/intelligence | entity precision/recall, resolution precision/coverage, edge precision/provenance, path correctness, dangling/orphan/duplicate rates |
| Incremental | canonical facts/graph/chunks/readiness and unchanged-case result equivalence versus clean full rebuild |
| Agent | workflow/tool selection, unnecessary provider/planner calls, rounds/tool calls, repair success, budget exhaustion behavior |
| Performance/cost | end-to-end and stage p50/p95, tokens, provider calls/cost, candidate/evidence counts, CPU/peak memory where applicable |
| Reliability/security | provider degradation, prompt-injection resistance, secret exclusion, authorization outcome, cancellation/timeout correctness |

Metric implementations specify denominator, zero/undefined handling, macro/micro aggregation, manual rubric, adjudication and confidence/variance. Manual labels record reviewer and disagreement resolution.

## Comparison and adoption

Report per-case and aggregate deltas from the simplest acceptable baseline. A complex method is accepted only when its versioned threshold/gain is approved and latency/cost/security/operations remain within accepted budgets. Reranker reports its input cap and quality gain; agent reports cases where it adds value versus deterministic workflows. Failure to beat the baseline rejects or disables the optional component—it does not weaken the baseline gate.

## Threshold acceptance

Thresholds are proposed after at least three repeatable production-like runs on declared reference environments/capacity classes. The evaluation owner proposes; product/reliability/security owners review relevant metrics; the release owner accepts them in immutable candidate evidence. A threshold change records rationale and cannot hide a regression by changing dataset/configuration silently.

## Outputs and evidence

Persist per-case candidates, evidence selections/rejections, graph paths, sanitized trace, answer/claims/citations, errors, budgets, latency/tokens/cost and scores. Export a manifest with frozen identities, raw result checksum, aggregates, threshold decisions, regressions and limitations. CI smoke tests may use deterministic fakes; provider-quality runs are separate reproducible release evidence.

## Release gates

Release blocks on invalid current citations, unsupported critical claims, failed insufficient-evidence threshold, critical graph integrity/provenance failure, full/incremental inequivalence, security/authorization failure, unapproved cost/latency regression or missing reproducibility identity. Numeric values live in release evidence, not hard-coded into this plan.
