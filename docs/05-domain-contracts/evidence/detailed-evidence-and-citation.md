# Detailed Evidence, Citation, and Claim Contract

Status: Accepted production v1 specification  
Authority: Evidence eligibility, citation identity, claim support, freshness, and validation  
Owner: Evidence owner  
Dependencies: `../../04-domain-and-data/identity-and-artifact-contract.md`, `../retrieval-evidence-assistant.md`  
Related source: `../../14-implementation-baseline/source-map.md`  
Related tests: evidence boundary, source range, stale, claim support, prompt injection, and citation regression suites  
Last verified: 2026-07-12

## Distinct objects

| Object | Meaning |
| --- | --- |
| Retrieval candidate | Unvalidated output from one retriever; cannot support an answer |
| Evidence | Immutable validated support object bound to repository/index/source/provenance |
| Citation | Reference from a message/claim to one evidence object and display locator |
| Claim | Atomic answer assertion with support level and citation set |

They must not be collapsed into message JSON or a generic confidence score.

## Evidence fields

Evidence has opaque ID, repository and opaque index-version IDs, canonical source/entity keys, evidence kind, valid file-level or inclusive 1-based range, content/source hash, safe preview policy, support type, provenance/producer refs, retrieval/selection reason codes, freshness status, created context and security validation version.

Support types are `source_exact`, `static_resolved`, `static_ambiguous`, `heuristic_inferred`, `llm_inferred`, or `user_supplied`. Exact facts normally omit numeric confidence. A calibrated method-specific confidence may accompany ambiguous/inferred support but never upgrades its authority.

## Eligibility validation

Before candidate promotion, validate authenticated access, repository/index match, active/explicit historical binding, source snapshot and canonical key existence, file/range bounds, content hash, blocked/secret policy, provenance/support schema and freshness. Graph evidence additionally validates same-version nodes/edge, every hop and its source support.

Unknown line ranges use file/entity-level evidence; line numbers are never invented. Secret/quarantined/skipped content cannot become evidence, prompt context, citation preview, trace or export.

## Claim support

Support levels are `direct`, `multi_hop`, `inferred`, and `insufficient`.

- Direct claims cite exact source/static facts.
- Multi-hop claims cite a validated bounded path with no undisclosed unsupported hop.
- Inferred claims name inference origin and cannot be presented as confirmed.
- Insufficient claims are removed, qualified as unknown, or cause an insufficient-evidence result.

Claim validation is deterministic. LLM output cannot create evidence/citation IDs, change support types, or approve itself.

## Freshness and history

Evidence remains bound to the index/source snapshot used at creation. After activation of a newer version it is historical/stale, not mutated into current evidence. UI may display retained safe preview and original locator with both version identities, validation result and a re-run action. A moved/changed source requires new evidence; aliases are not silently rewritten.

Retention preserves evidence referenced by retained messages/evaluation/audit according to policy. Repository deletion follows ownership/retention rules and never leaves cross-repository access paths.

## API and UI

Responses expose evidence/citation/claim separately plus capability, coverage, truncation and diagnostics. Citation chips open an authorized evidence route, which shows source, range, support/provenance label, index/freshness, claim linkage, validation result and code range action. Color is not the only support/stale indicator.

Validation failures are stable reason codes such as access mismatch, repository/index mismatch, source missing, range invalid, hash changed, blocked source, provenance invalid or stale. Stale is normally inspectable warning; invalid support cannot be used for a current claim.

## Metrics and tests

Measure syntactic citation validity, source/range/hash validity, citation relevance, claim support, unsupported-claim/hallucination rate, stale disclosure, insufficient-evidence accuracy, graph path correctness and provenance coverage. Test cross-repository/authorization denial, secret exclusion, malformed/out-of-range locators, re-index/move/delete, artifact corruption, inferred support, prompt injection and retained historical evidence.
