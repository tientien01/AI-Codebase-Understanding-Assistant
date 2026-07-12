# Retrieval, Trace, and Evaluation Runtime Contracts

Status: Accepted production v1 contract  
Authority: Normalized retrieval interchange, context selection, agent trace, and benchmark records  
Owner: Retrieval, assistant, and evaluation owners  
Dependencies: retrieval/evidence/assistant contracts and detailed evaluation plan  
Last verified: 2026-07-12

## Normalized candidate

Every retriever returns candidates before fusion:

```json
{
  "candidate_id": "cand_...",
  "repository_id": "repo_...",
  "index_version_id": "idx_...",
  "retriever": "symbol_exact",
  "retriever_version": "1",
  "entity_key": "symbol:v1:...",
  "source_key": "file:v1:...",
  "raw_score": 1.0,
  "rank": 1,
  "matched_terms": ["login"],
  "reason_codes": ["exact_qualified_name"],
  "support_type": "source_exact",
  "provenance_refs": ["prov_..."]
}
```

Retriever names are controlled enums: `exact`, `lexical`, `symbol`, `endpoint`, `metadata`, `documentation`, `configuration`, `test`, `graph`, and `semantic`. Provider-specific types stay behind adapters.

## Ranking configuration

Ranking configuration is immutable/versioned and records enabled retrievers, per-retriever candidate limits, normalization method, fusion method/parameters, boosts, filters, deduplication key, diversity policy, final limit, and context token budget.

Production v1 baseline comparison uses reciprocal-rank fusion unless a benchmark accepts another method:

```text
fused_score(candidate) = sum(weight_r / (rrf_k + rank_r))
```

Tie order is deterministic: fused score descending, best exact-support class, best individual rank, canonical entity key, then candidate ID. Raw scores from different retrievers are never directly added without an accepted normalization.

Deduplicate first by repository/index/entity/source span; merge reason/provenance lists without losing the highest rank per retriever. Apply access/security/index-version filters before ranking and evidence validation again before context selection.

## Evidence selection and context budget

The selector records selected/rejected candidate IDs and reason codes. Selection priorities are required question-type coverage, support strength, exact named targets, source diversity, non-overlapping spans, graph path completeness, freshness, and token cost.

Context output includes repository/index/config IDs, ordered evidence blocks, token estimate per block, omitted evidence summary, total budget, and truncation reason. It never truncates inside a citation span; if one required span exceeds budget, return a limited result or use a contract-defined smaller evidence window.

## Agent trace

Persist an append-only structured event sequence, never hidden chain-of-thought:

```json
{
  "trace_id": "trace_...",
  "repository_id": "repo_...",
  "index_version_id": "idx_...",
  "workflow_version": "assistant/v1",
  "ranking_config_id": "rank_...",
  "events": [
    {"seq": 1, "type": "question_classified", "payload": {"question_type": "api_flow", "confidence": 0.9}},
    {"seq": 2, "type": "tool_started", "payload": {"tool": "endpoint_lookup", "sanitized_input": {}}},
    {"seq": 3, "type": "tool_completed", "payload": {"candidate_ids": [], "duration_ms": 0}},
    {"seq": 4, "type": "sufficiency_decided", "payload": {"decision": "answer", "missing": []}},
    {"seq": 5, "type": "answer_validated", "payload": {"citation_ids": [], "unsupported_claims": 0}}
  ],
  "budget": {"max_rounds": 2, "rounds_used": 1, "input_tokens": 0, "output_tokens": 0, "provider_cost": null},
  "status": "completed"
}
```

Allowed event families cover classification, plan, tool start/completion/failure, candidate fusion, evidence selection, sufficiency, repair, provider call summary, citation validation, fallback, cancellation, and completion. Store sanitized inputs, IDs, counts, timings and decisions—not private reasoning, raw credentials, unrestricted source dumps, or provider payloads containing secrets.

## Evaluation case

One versioned case contains:

```yaml
id: api-flow-001
schema_version: evaluation-case/v1
fixture_id: fastapi_react_sample
fixture_revision: sha256:...
category: api_flow
question: How does the login flow work?
expected:
  entity_keys: []
  evidence_spans: []
  relation_paths: []
  answer_facts: []
  allowed_alternatives: []
policy:
  should_answer: true
  required_source_types: [endpoint, code]
  forbidden_claims: []
budgets:
  max_latency_ms: null
  max_input_tokens: null
tags: [auth, cross-stack]
```

Negative cases set `should_answer: false` and specify why evidence is absent/ambiguous. Expected evidence uses canonical keys plus source content hashes/ranges; free-text summaries alone are insufficient ground truth.

## Evaluation run identity

Every run freezes code revision, fixture/dataset version, index version, parser/resolver/pipeline versions, ranking/workflow configuration, model/embedding/reranker/provider, seed/temperature, capacity profile and timestamps. Per-case raw candidate/evidence IDs, trace, answer, citations, metrics, errors, latency, tokens and cost are retained. Aggregate reports without per-case reproducibility cannot block or approve release.
