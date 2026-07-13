# Phase 5 — Bounded Assistant Workflow

Status: Approved; AGT-002 sufficiency/repair/citation boundary is verified, AGT-003 is the next candidate, and Phase 5 exit/release qualification remain blocked by trace and evaluation thresholds

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
