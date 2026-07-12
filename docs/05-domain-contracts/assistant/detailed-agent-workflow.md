# Detailed Bounded Assistant Workflow

Status: Accepted production v1 specification  
Authority: Assistant routing, typed tools, sufficiency, budgets, trace, and fallback  
Owner: Assistant owner  
Dependencies: `../retrieval-evidence-assistant.md`, `../../10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md`, `../evidence/detailed-evidence-and-citation.md`  
Related source: `../../14-implementation-baseline/source-map.md`  
Related tests: routing, tool contract, budget, provider fault, refusal, citation, and trace privacy suites  
Last verified: 2026-07-12

## Routing hierarchy

```text
validate repository/index/access/capability
→ exact deterministic lookup when a named entity is present
→ typed deterministic workflow for overview/flow/impact/test/config questions
→ hybrid retrieval when exact/typed results are insufficient
→ constrained dynamic planning only for unresolved multi-step investigation
→ validate evidence sufficiency → generate/format → validate claims/citations
```

Exact file, symbol, endpoint, config key and error-code questions do not invoke a planner or semantic search when deterministic lookup is sufficient. LangGraph is not the default; the internal state machine is the production contract unless an accepted ADR authorizes another engine.

## Request and result

Request binds authenticated principal, `repository_id`, opaque `index_version_id` (or an explicit active-version resolution), conversation/context entity IDs, question, requested explanation mode and client request ID. Imported source text is data, never instructions.

Result includes outcome (`answered`, `limited`, `insufficient_evidence`, `cancelled`, `failed`), repository/index, capability state, answer claims, citation IDs, coverage, truncation, missing evidence, diagnostics, trace ID, budgets used and safe retry/remediation. Insufficient evidence is a valid successful product outcome.

## Typed tool contract

Every allowlisted tool has JSON-serializable versioned input/output and enforces access/version/budgets independently. Output includes repository/index, capability, candidates or evidence/path IDs, coverage, truncation, diagnostics, duration and retryability.

Tools cover exact file/symbol/endpoint/config lookup, lexical/metadata/document/test retrieval, bounded graph projection/path, impact, optional semantic retrieval, evidence validation and source range reads. Tools never return raw credentials, blocked source, unrestricted graph/repository dumps, or provider-specific objects.

## Workflow state

Persist opaque IDs and structured decisions: request identity, question type, resolved entities, selected workflow, tool calls/results, normalized candidates, selected/rejected evidence reason codes, sufficiency decision, repair attempts, provider summary, claims/citations, terminal outcome and budget consumption. Do not store hidden chain-of-thought, raw secrets, full prompts by default, or unrestricted source dumps.

Question types are controlled and versioned: exact entity, architecture/onboarding, endpoint/flow, impact/change, debugging/error, database/model, configuration/deployment, tests, documentation, security and unknown/clarification.

## Sufficiency

Sufficiency is a deterministic policy by question type and support requirement, not a generic `evidence_score`. Examples:

- exact entity: validated exact observation and source location;
- endpoint behavior: endpoint/handler plus supporting source;
- flow: validated start plus supported path with unsupported hops disclosed;
- impact: validated target plus bounded typed neighbors; absence is `unknown` within coverage;
- architecture: multiple representative deterministic artifacts/docs with coverage;
- test relation: deterministic relation or explicit none-found-within-coverage result.

Heuristic/LLM-inferred data may guide retrieval but is labeled and cannot solely support a confirmed critical claim. Conflicting evidence is preserved and disclosed.

## Repair and budgets

One or more repair rounds may broaden/alter deterministic queries or request a bounded additional graph path. The immutable workflow configuration caps tool calls, rounds, per-tool candidates, graph depth/nodes/edges, selected evidence, execution time, provider calls, context/input/output tokens and provider cost. Cancellation and timeout are checked before/after every tool/provider boundary.

Budget exhaustion returns a limited/insufficient result with what was searched; it never silently increases limits. Repeated equivalent tool calls are deduplicated. Cache keys include access boundary, repository/index, normalized request, tool/config version and security policy; activation and authorization changes invalidate reuse.

## Generation and validation

The provider receives only selected validated evidence within context budget. Claims are structured and mapped to citations. Deterministic validation confirms cited evidence identity/scope/version/location/support and rejects unsupported files/symbols/routes/relations. One bounded repair may remove or qualify invalid claims; otherwise return insufficient evidence.

Provider timeout/rate/auth/outage returns deterministic results when a template can faithfully express them, otherwise a limited provider-unavailable result. It never fabricates prose.

## Verification

Benchmark exact questions to prove planner/vector avoidance; positive, negative, ambiguous, stale, unsupported-language, incomplete-graph, provider-outage, prompt-injection and large-repository cases; enforce budgets and cancellation; compare deterministic/hybrid/agent workflows on quality, latency and cost; scan traces for secrets and verify replay/debug read models without hidden reasoning.
