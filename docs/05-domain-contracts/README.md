# Domain Contracts

Contracts are normative boundaries. Each implementation task links only the contracts it changes.

## Indexing contract

`scan → parse → resolve → emit candidates → normalize graph → enrich optional semantics → validate → publish`.

- Every phase has typed input/output and declared artifact dependencies.
- Parsers emit file-local facts and never write database rows.
- Resolvers map references to canonical entities and do not use LLMs for statically resolvable relations.
- Graph normalization records dropped/changed candidates as diagnostics.
- Publisher activates only validated versions transactionally.

## Evidence contract

A retrieval result becomes evidence only after repository/index/source existence, range, security filter, freshness, and support type validation. LLMs cannot invent evidence IDs, locations, symbols, endpoints, or graph edges.

## Capability contract

Readiness is computed from required artifacts and validation results. A missing artifact cannot be masked by a generic `indexed` status.

## Detailed specifications

- `indexing/detailed-indexing-pipeline.md`
- `parsing/detailed-parser-output-schema.md`
- `assistant/detailed-agent-workflow.md`
- `evidence/detailed-evidence-and-citation.md`

They define stage behavior, schemas, confidence/provenance, agent nodes and guardrails, evidence lifecycle, citations, fallbacks, and production extensions. Tasks must reference the relevant detailed file, not this summary alone.
