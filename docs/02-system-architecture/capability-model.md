# Capability Readiness Model

Status: Accepted  
Authority: Repository-version capability semantics  
Owner: Indexing and product owners  
Dependencies: Indexing, evidence, API and UX contracts  
Last verified: 2026-07-12

## Purpose

A repository is not simply `indexed`. Each index version exposes only capabilities justified by present artifacts and validation results.

## States

| State | Meaning | Required behavior |
| --- | --- | --- |
| `ready` | All mandatory artifacts and validations pass | Enable capability and disclose index version |
| `limited` | Safe partial result is available with known coverage limits | Enable with limitation/coverage disclosure |
| `unavailable` | Required artifacts or supported analysis do not exist | Disable action and explain prerequisite |
| `failed` | Required build/validation attempted and failed | Show diagnostic reference and recovery action |
| `stale` | Capability is bound to a superseded/source-changed version | Preserve inspectability, warn, and prefer current evidence |

`building` is a job/version lifecycle state, not a capability result.

## Minimum production capabilities

| Capability | Required artifacts | Validation examples |
| --- | --- | --- |
| File exploration | source manifest, file records | path boundary, checksum, readable source |
| Symbol search | parsed symbol artifacts, lexical index | schema validity, source spans, supported language |
| Endpoint exploration | endpoint records, handler relations | route uniqueness rules, handler evidence |
| Graph projection | normalized nodes/edges with provenance | no dangling critical edges, bounded query support |
| Impact analysis | resolved target plus typed incoming/outgoing relations | path validity, coverage disclosure |
| Evidence retrieval | eligible source/chunk/metadata records | repository/version/range/security/freshness checks |
| Semantic search | embedding artifacts and compatible configuration | dimension/model/config consistency |
| Grounded assistant | retrieval, evidence selection, citation validation | sufficiency and refusal behavior |

The detailed artifact list and thresholds belong to owning contracts and versioned validators.

## Language profile

Language support is reported per capability, not by a single “supported language” badge. Production v1 uses:

- **Reference/deep:** Python and FastAPI fixtures define the deepest guaranteed profile.
- **Structural:** JavaScript, TypeScript, and React guarantee declared syntax/entity/import capabilities, not Python-equivalent CFG/DFG depth.
- **Document/config:** Markdown, JSON, YAML, TOML, Docker-related files and safe example configuration expose declared document/config facts.

The exact matrix is generated from golden fixtures by `INT-004`; until then the UI must avoid unverified “full support” claims.

## API and UI contract

Read APIs return capability state, reason code, index version, coverage summary, validation reference, and remediation when applicable. Frontend pages render explicit loading, empty, limited, stale, failed, and unavailable states; they never infer readiness from an HTTP 200 or a generic repository status.
