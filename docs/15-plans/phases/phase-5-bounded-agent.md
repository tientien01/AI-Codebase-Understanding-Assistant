# Phase 5 — Bounded Assistant Workflow

Status: Approved; AGT-001 through AGT-003 and the deterministic EVA-002 assistant/evaluation CI smoke gate are verified, while Phase 5 exit/release qualification remains blocked by accepted evaluation thresholds and later security/auth retention policy delivery

## Outcome

The assistant selects typed tools, checks evidence sufficiency, performs bounded retrieval repair, and returns citation-validated answers or explicit limitations with a privacy-safe persistent trace.

## Tasks

`AGT-001` through `AGT-003`, followed by `EVA-002` agent gates.

## Entry

Retrievers, evidence selector, context budget, deterministic fakes, and negative evaluation cases are stable.

## Exit gates

- Classifier, plan, tools, observations, sufficiency and final result use versioned typed schemas.
- Tool allowlist, maximum rounds, token/time/cost budgets, cancellation and provider fallbacks are enforced.
- LLM output cannot create evidence identities or override static facts.
- Citation validation and insufficient-evidence behavior pass regression thresholds.
- Conversations/traces persist with redaction, retention and replay/debug read models.

## Evidence

Tool-selection report, repair ablation, hallucination/refusal benchmark, provider-fault suite, trace privacy/integration tests.

`AGT-001` adds immutable versioned workflow/tool contracts, an explicit exact/hybrid allowlist, deterministic exact avoidance/fallback routing, tool-call/time/context limits, cancellation, deduplication and safe observations. It does not implement multi-round sufficiency repair, claim/citation validation, persistent traces or evaluation thresholds.

`AGT-002` adds deterministic question-specific sufficiency, one controlled budgeted repair, structural claim-to-selected-current-citation validation and provider fail-closed acceptance. It does not add persistent trace/conversation storage, semantic entailment qualification or accepted agent evaluation thresholds.

`AGT-003` atomically persists redacted conversation messages, claims, citations and an allowlisted ordered trace across local SQLite and the accepted PostgreSQL schema. Internal replay enforces repository ownership and deterministic ordering. Public history endpoints, retention scheduling, authenticated-principal delivery and accepted agent evaluation thresholds remain outside this task.

`EVA-002` adds a named CI job combining the existing assistant, graph/readiness, incremental/equivalence and versioned retrieval evaluation suites with a content-addressed synthetic smoke policy. Its metric floors are classified `ci_regression_only`; they are not accepted agent, provider, latency, cost or release thresholds.
