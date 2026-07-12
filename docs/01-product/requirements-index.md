# Canonical Product Requirements Index

This index routes requirements to their detailed acceptance flow in `specifications/requirements-and-use-cases.md`. It does not duplicate the complete scenarios.

## Priority model

- **P0:** required for production safety or the primary end-to-end product.
- **P1:** required for a strong production product but may follow the first internal deployment.
- **P2:** differentiator or extension activated after P0/P1 quality gates.
- **Deferred:** outside production v1.

## Repository and import

| ID | Requirement | Priority |
| --- | --- | --- |
| U001 | Import folder, ZIP, or local source | P0 |
| U002 | Preview source before indexing | P0 |
| U003 | Detect and resolve duplicate repositories | P1 |
| U004 | Import public GitHub repository | P0 |
| U005 | Synchronize a GitHub source | P1 |
| U024 | Configure ignore rules | P0 |
| U025 | Secret scanning and security warnings | P0 |
| U028 | Delete a repository and owned data safely | P0 |

## Index lifecycle and quality

| ID | Requirement | Priority |
| --- | --- | --- |
| U006 | Observe indexing progress | P0 |
| U007 | Re-index a repository | P0 |
| U008 | Inspect history, warnings, skipped, and failed files | P0 |
| U009 | Detect stale indexes | P0 |
| U037 | Inspect index quality and validation | P0 |
| U038 | Inspect readiness by capability | P0 |
| U040 | Compare index versions | P1 |
| U043 | Incremental re-index with affected set | P0 |
| U044 | Inspect unresolved references | P1 |

## Codebase exploration

| ID | Requirement | Priority |
| --- | --- | --- |
| U010 | View repository overview | P0 |
| U011 | Explore files and content | P0 |
| U012 | Inspect symbol details | P0 |
| U013 | Receive a justified reading path | P1 |
| U019 | Explore endpoints | P1 |
| U020 | Trace request/runtime flow | P1 |
| U021 | Explore bounded dependency graph | P1 |
| U039 | Inspect graph relation provenance | P0 |
| U041 | Follow guided tours | P2 |
| U042 | Explore architecture layers/components | P1 |
| U045 | Explore domain/business flows | P2 |

## Search, evidence, and assistant

| ID | Requirement | Priority |
| --- | --- | --- |
| U014 | Search with type/source/filter support | P0 |
| U015 | Inspect evidence and citations | P0 |
| U016 | Ask repository questions with evidence | P0 |
| U017 | Ask using selected workspace context | P1 |
| U018 | Persist chat and expose stale citations | P1 |
| U032 | Plan bounded retrieval for codebase questions | P1 |
| U033 | Orchestrate typed tools | P1 |
| U034 | Verify evidence and hallucination constraints | P0 |
| U035 | Perform bounded multi-step investigation | P1 |
| U036 | Explain code and personalize learning depth | P2 |

## Impact, tests, settings, and evaluation

| ID | Requirement | Priority |
| --- | --- | --- |
| U022 | Analyze impact of a file/symbol/change | P1 |
| U023 | Find related tests | P1 |
| U026 | Configure LLM/embedding providers safely | P1 |
| U027 | Manage storage and repository data | P1 |
| U029 | Run a deterministic sample demo | P1 |
| U030 | Run evaluation and demo checklist | P0 |
| U031 | Multi-user sharing and RBAC | Deferred for v1; single-operator authentication/authorization is P0 |

## Cross-cutting production requirements

| ID | Requirement | Authority |
| --- | --- | --- |
| NFR-REL-001 | Failed/restarted workers do not lose authoritative job state | Indexing contract |
| NFR-REL-002 | Failed builds never replace the active index | Data/index contract |
| NFR-SEC-001 | Imported source is untrusted and never executed | Security architecture |
| NFR-SEC-002 | Secrets are excluded before parsing, embedding, logging, or export | Security architecture |
| NFR-SEC-003 | L3 authenticates the operator and authorizes every repository/evidence/artifact operation | Security architecture |
| NFR-AI-001 | Technical claims require validated evidence or explicit limitation | Evidence contract |
| NFR-AI-002 | Agent workflow is bounded by calls, rounds, depth, time, tokens, and cost | Assistant contract |
| NFR-DATA-001 | Production schema changes use versioned migrations | Database design |
| NFR-OPS-001 | Required dependencies expose health, telemetry, recovery, and runbooks | Reliability architecture |
| NFR-UX-001 | Every async page supports applicable loading/empty/error/retry/stale/limited states | UX architecture |
| NFR-EVAL-001 | Retrieval/graph/citation/agent regressions block release | Evaluation policy |

## Requirement completion

A requirement is complete only when its contract is implemented, linked tasks are complete, automated/manual acceptance tests pass, baseline is updated, and immutable release evidence is present.
