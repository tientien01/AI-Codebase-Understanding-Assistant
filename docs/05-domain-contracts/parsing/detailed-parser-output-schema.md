# Detailed Parser, Resolver, and Graph-Candidate Schema

Status: Accepted production v1 specification  
Authority: File-local IR, resolver output, graph-candidate interchange, and validation  
Owner: Code-intelligence owner  
Dependencies: `../parsing-and-graph.md`, `../../04-domain-and-data/identity-and-artifact-contract.md`  
Related source: `../../14-implementation-baseline/source-map.md`  
Related tests: parser golden, resolver accuracy, canonical identity, provenance, and schema compatibility suites  
Last verified: 2026-07-12

## Pipeline boundary

```text
canonical scan item → language adapter → ParsedFile IR
→ deterministic resolver → ResolvedReference
→ optional supported CFG/DFG → GraphCandidate
→ graph normalization/validation
```

Parsers read only indexable canonical-inventory files, never write database rows, never read skipped/secret files, and never guess cross-file identity. Resolvers do not use LLMs for statically resolvable relations. All schemas are versioned, JSON-serializable and deterministic for the same inputs/component versions.

## Common envelope

Every artifact/item carries repository and opaque index-version IDs, canonical file key, producer name/version/stage, schema version, source content hash, extraction/support type, valid inclusive 1-based source spans, diagnostics and extension metadata. Canonical keys are generated only by the shared `kind:v1:` library defined by the identity contract.

Exact extraction uses support type rather than an arbitrary confidence. Ambiguous/heuristic results may carry a method-specific calibrated score in `[0,1]`; the score never replaces origin/support and no global numeric band is invented here.

## ParsedFile IR

```json
{
  "schema_version": "parsed-file/v1",
  "repository_id": "repo_...",
  "index_version_id": "idx_...",
  "file_key": "file:v1:backend/app/auth.py",
  "content_hash": "sha256:...",
  "language": "python",
  "adapter": {"name": "python-ast", "version": "..."},
  "symbols": [],
  "imports": [],
  "exports": [],
  "endpoints": [],
  "api_calls": [],
  "config_keys": [],
  "document_sections": [],
  "tests": [],
  "raw_references": [],
  "diagnostics": []
}
```

Items use local IDs within the artifact plus name/kind/signature/qualified-name where deterministically known, parent local ID, source span, extraction method and safe metadata. Raw imports/calls/API/config/test references preserve source text/normalized form and location but do not claim a target.

Language capability is declared per adapter and golden fixture: recognition, syntax parse, symbols, imports/exports, endpoints, calls, models/schemas, tests, docs/config, CFG/DFG and framework rules. Unsupported behavior emits a diagnostic and cannot be marketed from extension recognition alone.

## Resolver output

```json
{
  "schema_version": "resolved-reference/v1",
  "id": "ref_...",
  "repository_id": "repo_...",
  "index_version_id": "idx_...",
  "source_file_key": "file:v1:backend/app/api/auth.py",
  "source_entity_key": "symbol:v1:...",
  "reference_type": "call",
  "raw_reference": "AuthService.login",
  "outcome": "resolved",
  "target_keys": ["symbol:v1:..."],
  "resolution_method": "python-qualified-name/v1",
  "support_type": "static_resolved",
  "source_spans": [],
  "diagnostic_ids": []
}
```

Outcome is `resolved`, `ambiguous`, or `unresolved`. Ambiguous candidates and unresolved reason are retained; nothing is silently dropped. Supported methods include language import/export rules, qualified symbols/inheritance, accepted framework endpoint-handler rules, frontend/backend route matching, test-target rules, config usage and model/schema usage. Dynamic behavior remains unresolved/limited unless deterministic evidence exists.

## Graph candidates

Node candidates identify canonical key/type/label/source location and provenance. Edge candidates identify canonical source/target keys, one canonical relation direction, origin, support type, evidence/provenance references, producer/version and optional discriminator for distinct call sites.

Allowed origins are controlled: `parser_exact`, `resolver_exact`, `framework_rule`, `heuristic`, `llm_inferred`, `user_confirmed`. LLM-inferred candidates are optional enrichment only, pass schema/security validation, remain inferred, and cannot replace parser/resolver facts.

Do not emit inverse duplicates such as both `calls` and `called_by` or `imports` and `imported_by`; reverse traversal is a query direction. Relation types and endpoint/config/entity normalization come from the versioned graph schema.

## Validation and compatibility

- File keys exist in the same canonical scan inventory and content hash matches.
- Spans are valid or explicitly file-level; no fabricated lines.
- Canonical keys parse and remain repository-local.
- Target keys for resolved references/candidates exist or produce diagnostics.
- Producer/schema versions are compatible with the consuming stage.
- Output contains no blocked content, host path or credential.
- Ordering and serialization are deterministic for golden comparisons.

Schema evolution is additive within a compatible version or creates a new version plus migration/adapter. Parser cache keys include file hash, adapter/parser/schema/framework-rule versions and relevant config. Golden fixtures cover malformed/unsupported syntax, aliases, ambiguity, dynamic behavior, line shifts, moves/renames, source security and deterministic repeat runs.
