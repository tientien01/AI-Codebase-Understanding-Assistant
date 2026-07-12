# Identity, Provenance, and Artifact Contract

Status: Accepted production v1 contract  
Authority: Cross-version identity, provenance, artifact manifests, and activation  
Owner: Data and indexing owners  
Dependencies: detailed data/storage and indexing specifications, ADR-0001  
Last verified: 2026-07-12

This contract refines the examples in the detailed specifications. Database migrations and typed models must implement these semantics before Phase 3 completion.

## Identity layers

| Identity | Purpose | Stability |
| --- | --- | --- |
| Database ID | Internal row/reference identity | Immutable for row lifetime; never parsed for meaning |
| Canonical key | Semantic identity inside one repository across index versions | Stable under line-only/content-body changes; changes when semantic address changes |
| Versioned record ID | One entity observation in one index version | Immutable and bound to repository/index version |
| Evidence ID | One validated support object | Immutable, opaque, repository/version bound |

Canonical keys are repository-local. Every stored/query object also carries `repository_id`; callers must never infer repository ownership from the key text.

## Canonical key format

Keys are UTF-8 strings with lowercase kind/version prefix and percent-encoded segments:

```text
<kind>:v1:<segment>[:<segment>...]
```

- Normalize repository paths to relative POSIX form, remove `.` segments, reject `..`, preserve case, and never include an absolute host path.
- Normalize language/kind/method fields to lowercase canonical enums.
- Percent-encode literal `:`, `%`, control characters and non-safe path characters inside segments.
- One shared key library owns generation and parsing; parsers do not hand-build keys.

| Entity | Canonical form | Example |
| --- | --- | --- |
| File | `file:v1:<path>` | `file:v1:backend/app/auth.py` |
| Module | `module:v1:<language>:<module-name>` | `module:v1:python:app.auth` |
| Symbol | `symbol:v1:<language>:<kind>:<file-key>:<qualified-name>[:<overload>]` | `symbol:v1:python:method:file%3Av1%3Aapp/auth.py:AuthService.login` |
| Endpoint | `endpoint:v1:<protocol>:<method>:<normalized-route>:<handler-key>` | `endpoint:v1:http:post:/api/login:<encoded-handler-key>` |
| Config | `config:v1:<file-key>:<qualified-key>` | `config:v1:<encoded-file-key>:services.api.image` |
| Document section | `doc:v1:<file-key>:<heading-anchor>:<occurrence>` | `doc:v1:<encoded-file-key>:installation:1` |
| Chunk | `chunk:v1:<source-key>:<chunk-kind>:<ordinal>:<content-hash-prefix>` | content-addressed observation, not semantic source identity |
| Graph edge | `edge:v1:<type>:<source-key>:<target-key>:<discriminator>` | discriminator distinguishes call sites/multiple evidence |

Overload discriminator is omitted when the language cannot overload at the same qualified address. When required, it is a hash of normalized parameter kinds/types, not line numbers.

## Change semantics

| Change | Canonical-key behavior | Comparison behavior |
| --- | --- | --- |
| Lines inserted/body edited | File/symbol key unchanged | New versioned observation and content hash |
| Symbol signature changes | Key unchanged unless overload identity changes | Signature diff recorded |
| Symbol rename | New key | Optional high-confidence `renamed_from` candidate; never silently merge |
| File move/rename | File and contained file-addressed symbol keys change | Move detector records candidate using content/symbol fingerprints |
| Endpoint handler moves | Endpoint key changes because handler key changes | Route-equivalent comparison may link versions |
| Route/method changes | Endpoint key changes | Breaking-change candidate |

Rename/move candidates are inferred version-diff relations with provenance and confidence, not identity aliases, until accepted by deterministic rules.

## Provenance envelope

Every parsed/resolved/graph/evidence fact carries:

```json
{
  "repository_id": "repo_...",
  "index_version_id": "idx_...",
  "producer": {"stage": "resolve", "name": "python-call-resolver", "version": "1"},
  "support_type": "static_resolved",
  "source_spans": [{"file_key": "file:v1:...", "start_line": 10, "end_line": 12, "content_hash": "sha256:..."}],
  "confidence": 1.0,
  "diagnostic_ids": []
}
```

`support_type` is one of `source_exact`, `static_resolved`, `static_ambiguous`, `heuristic_inferred`, `llm_inferred`, or `user_supplied`. LLM output cannot produce `source_exact` or `static_resolved`. Confidence is omitted for exact facts unless the schema requires a numeric value; it never replaces support type.

## Index manifest

`manifest.json` is immutable after a version reaches a terminal build state. Corrections create a new index version.

```json
{
  "schema_version": "index-manifest/v1",
  "repository_id": "repo_...",
  "index_version_id": "idx_...",
  "sequence": 4,
  "base_index_version_id": "idx_...",
  "build_kind": "full",
  "source": {"type": "folder", "revision": null, "snapshot_sha256": "..."},
  "pipeline": {"version": "...", "configuration_sha256": "..."},
  "status": "ready",
  "artifacts": [
    {"type": "scan_result", "schema_version": "scan/v1", "uri": "artifacts/scan-result.json", "sha256": "...", "bytes": 0, "records": 0, "required": true}
  ],
  "capabilities": {},
  "coverage": {},
  "validation": {"status": "passed", "report_uri": "artifacts/validation-report.json", "report_sha256": "...", "critical_issues": 0},
  "timestamps": {"started_at": "...", "finished_at": "..."}
}
```

Allowed `build_kind`: `full`, `incremental`. Allowed manifest status: `building`, `validating`, `ready`, `ready_with_warnings`, `failed`, `cancelled`; database lifecycle may later add `active`, `superseded`, and `expired` without mutating the terminal artifact manifest.

## Artifact rules

- URI is relative to the version artifact root or an opaque storage-port key; it never exposes a host absolute path.
- Checksum is SHA-256 over exact stored bytes. Readers verify before use and report corruption.
- Schema version is mandatory for every structured artifact.
- Artifact writes use temporary names/multipart staging, checksum verification, then atomic finalize where the backend permits.
- Required artifact types are derived from requested capabilities and recorded before validation. A missing required artifact makes that capability unavailable and blocks activation when mandatory.
- Debug/provider payloads have separate retention/redaction and are never mandatory evidence artifacts.

## Activation transaction

Activation requires: terminal ready manifest; checksum-valid mandatory artifacts; zero critical validation issues; compatible database records/search indexes; and capability calculation. One database transaction locks the repository, verifies the expected previous active version, marks the new version active, marks the previous version superseded, and writes an audit event. Failure leaves the prior active version unchanged. Filesystem pointer files may be caches only and cannot be activation authority.
