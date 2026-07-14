# Detailed REST API Contract

Status: Accepted semantic target; current implementation OpenAPI baseline verified by `FND-003`
Authority: HTTP semantics until verified OpenAPI becomes machine-readable authority  
Owner: API owner  
Dependencies: `../README.md`, domain/data/security/reliability/UX contracts  
Related source: `../../14-implementation-baseline/api-coverage.md`  
Related artifact: `../artifacts/openapi-v1.json`
Related tests: OpenAPI drift, auth, idempotency, pagination, range, projection, error, and E2E contract suites  
Last verified: 2026-07-12

Base path is `/api/v1`. `/health/live` and `/health/ready` are operational exceptions. CLI/MCP adapters invoke the same authorized application use cases and do not duplicate business logic.

## Universal request contract

- Production requires an authenticated single-operator principal; every repository/evidence/artifact/trace operation authorizes ownership/scope. Blank/shared development-token bypass is forbidden.
- Accept or generate `X-Request-ID`; return it on every response and in the error envelope.
- Mutating import confirmation, index submission/cancellation, repository deletion and other retryable operations require `Idempotency-Key`. Reuse with a different normalized request is `409 IDEMPOTENCY_CONFLICT`.
- Repository reads bind an explicit opaque `index_version_id` or resolve the active version once at request start and return it. Integer sequence is display metadata only.
- Lists use opaque stable cursors with deterministic unique ordering. Server-enforced maximum page size applies.
- Expensive operations are asynchronous and return `202` plus resource/job ID and status URL. Cancellation is explicit and durable.
- Conditional headers/checks are used where stale mutation would be unsafe. Upload, body, range, graph, query and provider budgets are enforced before expensive work.

Authentication behavior is fixed: missing/invalid credentials return `401 AUTHENTICATION_REQUIRED` with `WWW-Authenticate`; an authenticated principal requesting a repository-scoped resource outside its ownership boundary receives non-disclosing `404 RESOURCE_NOT_FOUND` and a security audit event. CSRF failure for browser-session mutations is `403 CSRF_VALIDATION_FAILED`. CLI/MCP Bearer requests do not use CSRF but still enforce origin-independent authorization and rate limits.

Idempotency records store principal, operation, key, normalized request hash, status and resulting resource/response reference. Same key plus same hash returns the original outcome, including an in-progress `202`; same key plus different hash is `409 IDEMPOTENCY_CONFLICT`. Records outlive client retry windows according to the accepted retention configuration.

## Universal response metadata

Repository/index-derived responses include:

```json
{
  "repository_id": "repo_...",
  "index_version_id": "idx_...",
  "capability": {"state": "ready", "reason_codes": []},
  "coverage": {},
  "truncation": {"truncated": false, "reason": null},
  "request_id": "req_..."
}
```

Capability states are only `ready`, `limited`, `unavailable`, `failed`, or `stale`. Job/index/source/repository lifecycle uses separate fields.

## Canonical wire schemas

Until generated OpenAPI is checked and drift-tested, implementations use these minimum wire schemas. Fields are required unless marked nullable/optional; timestamps are UTC RFC 3339; IDs are opaque strings and canonical keys are percent-encoded path/query values.

### Common types

| Type | Required fields |
| --- | --- |
| `Page<T>` | `items: T[]`, `next_cursor: string|null`, `request_id: string` |
| `CapabilityStatus` | `state: ready|limited|unavailable|failed|stale`, `reason_codes: string[]`, `validation_ref: string|null`, `remediation: string|null` |
| `Coverage` | `measured: object`, `unknown: string[]`; values must name units/denominators |
| `Truncation` | `truncated: boolean`, `reason: string|null`, `continuation_token: string|null` |
| `SourceRange` | `file_key`, `start_line: integer|null`, `end_line: integer|null`, `content_hash`; both lines are present together and inclusive |
| `AsyncRef` | `operation_id`, `status_url`, `state`, related `repository_id/job_id/index_version_id` when applicable |

### Operator access schemas

`BootstrapRequest` contains `display_name` and `password`; the one-time bootstrap credential is supplied only in `X-Bootstrap-Credential`. `LoginRequest` contains only `password`. Successful bootstrap/login returns principal identity, absolute expiry and a one-time CSRF token while setting the opaque `aica_session` cookie as `HttpOnly`, `Secure`, `SameSite=Strict` in production.

`ApiTokenCreateRequest` contains a bounded name and `expires_in_seconds`. Creation returns `token_id`, name, expiry and the raw `token` exactly once. Session/API-token/password verifier values and audit responses never expose stored hashes.

### Import schemas

`POST /import-sessions/zip` accepts multipart `file` and optional `display_name`. `POST /import-sessions/folder` accepts repeated `files` plus equal-length normalized `relative_paths` and optional `display_name`. Public Git accepts JSON `{url, ref|null, display_name|null}`; credentials, custom hosts, ports and schemes are invalid.

Uploads are streaming but not resumable in production v1. An interrupted request does not publish an `ImportSession`; temporary bytes remain under an unowned upload token and are deleted by bounded TTL cleanup. Only after the complete upload hash/size and boundary checks pass is a session created.

`ImportSession` returns `import_session_id`, `state`, `source_type`, `expires_at`, `upload_bytes`, `source_fingerprint|null`, and `request_id`.

`ImportPreview` returns `import_session_id`, `state=preview_ready`, `snapshot_candidate_id`, `policy_version`, `source_fingerprint`, `total_files`, `total_bytes`, `indexable_files`, `indexable_bytes`, `languages[]`, `skip_counts[]`, `security_warnings[]`, `duplicate_candidates[]`, `limits`, `confirmation_allowed`, and `request_id`. It never returns secret content or host paths.

Confirm request is `{display_name, start_indexing: boolean, index_profile, duplicate_action}` and requires `Idempotency-Key`. Response is `201`/`202` with `repository_id`, `source_snapshot_id`, `job_id|null`, `index_version_id|null`, `status_url|null`, and `request_id`.

### Job/version schemas

`CreateIndexJobRequest` is `{build_kind: full|incremental, base_index_version_id|null, requested_capabilities: string[], profile}`. The server may force `full` and returns the reason. Response is `202 AsyncRef` or `409 INDEX_ALREADY_RUNNING` with the existing `job_id`.

`IndexJob` includes `job_id`, `repository_id`, `requested_build_kind`, `effective_build_kind`, `state`, `current_attempt_id|null`, `lease_observed_at|null`, `stage`, `progress{completed,total,unit}|null`, `cancellation_requested_at|null`, `target_index_version_id`, `base_index_version_id|null`, `warning_count`, `error{code,message,retryable}|null`, and timestamps. Lease owner/generation are operator diagnostics and not exposed to ordinary clients.

Cancel response is `202` with job identity and `cancellation_requested_at`; if activation already committed it is `409 CANCELLATION_TOO_LATE` with the successful active `index_version_id`.

`IndexVersion` includes opaque ID, display `sequence`, lifecycle, build kind, source snapshot/base IDs, manifest key/checksum, validation summary, capability map, coverage, started/finished/activated timestamps and failure code. Integer `sequence` is never accepted as an identity parameter.

### Exploration/search/graph schemas

File/symbol/endpoint list responses are `Page<T>` and bind repository/index/capability/coverage. Source content requires `start_line` and `end_line` or a server-default bounded first range, and returns `file_key`, index version, total lines/bytes, actual range, encoding, content hash, text lines, and truncation.

Search request is `{index_version_id|null, query, query_type: exact|lexical|hybrid, entity_types[], paths[], languages[], final_limit}`. `final_limit` is capped by server configuration. Response separates `candidates[]` from `evidence[]`; every candidate includes candidate/entity/source keys, retriever/version, rank, reason codes and support/provenance references.

Graph projection/path request includes `index_version_id|null`, `view`, `root_keys[]`, `node_types[]`, `edge_types[]`, `direction`, `max_depth`, `max_nodes`, `max_edges`. Response includes nodes/edges, included/available counts or estimates, coverage, truncation, unsupported hops and continuation token. Client bounds cannot exceed server maxima.

### Evidence/assistant schemas

`Evidence` follows the evidence contract and includes opaque evidence/repository/index IDs, source/entity keys, evidence kind, source range or file-level locator, support type, provenance refs, freshness, safe preview, selection reasons and validation status. `Citation` contains `citation_id`, `evidence_id`, `claim_id`, and display locator. `Claim` contains `claim_id`, text, support level and citation IDs.

Assistant request is `{index_version_id|null, conversation_id|null, question, context_entity_keys[], explanation_mode, client_limits|null}`. Client limits can only reduce server maxima. Result includes outcome, claims, citations, evidence summaries, capability, coverage/truncation, missing evidence, diagnostics, trace ID, budget use and provider degradation.

## Error envelope

```json
{
  "error": {
    "code": "CAPABILITY_NOT_READY",
    "message": "Safe user-facing message.",
    "details": {},
    "request_id": "req_...",
    "retryable": false,
    "retry_after_seconds": null
  }
}
```

`details` is schema-defined and never contains secrets, host paths, raw source/provider payloads or stack traces. Clients do not infer retryability from HTTP/status text. `INSUFFICIENT_EVIDENCE` is normally a `200` assistant outcome, not an HTTP error.

## Health

| Endpoint | Semantics |
| --- | --- |
| `GET /health/live` | Process event loop is alive; no dependency claims |
| `GET /health/ready` | Required configuration, schema, PostgreSQL, Redis delivery, artifact store and migration compatibility pass; optional provider failure is reported by capability, not global unreadiness |

## Resource surface

Exact request/response schemas are generated into OpenAPI. These operations and semantics are mandatory:

### Authentication and operator access

```text
POST   /auth/bootstrap
POST   /auth/login
POST   /auth/logout
GET    /auth/session
POST   /auth/tokens
DELETE /auth/tokens/{token_id}
```

Bootstrap is available only while no initialized operator password verifier exists. Browser-session mutations require an exact configured Origin and the session-bound `X-CSRF-Token`; safe reads do not require CSRF. Named API tokens use only `Authorization: Bearer <token>` and are individually expirable/revocable. Production rejects `X-API-Key`, blank authentication and the development shared token. Repository path requests authorize the authenticated principal against `owner_principal_id`; missing and foreign repositories share `404 RESOURCE_NOT_FOUND`, and denials append privacy-safe audit events.

### Import sessions

```text
POST   /import-sessions/zip
POST   /import-sessions/folder
POST   /import-sessions/upload-folder/start
POST   /import-sessions/{session_id}/upload-folder-batch
POST   /import-sessions/{session_id}/upload-folder-complete
POST   /import-sessions/public-git
GET    /import-sessions/{session_id}/status
GET    /import-sessions/{session_id}/preview
POST   /import-sessions/{session_id}/confirm
DELETE /import-sessions/{session_id}
```

Upload/folder paths use normalized relative paths. Browser folder import first submits a bounded manifest, uploads no more than 500 files per multipart batch, and explicitly completes the session; incomplete, duplicate, unsafe or over-quota batches fail with a stable domain error and clean staging. ZIP entry count, expanded size, compression ratio and actual streamed bytes remain hard archive-envelope gates; a correctly declared individual source file above the indexing limit is reported as skipped rather than rejecting an otherwise valid archive. Public Git accepts only the production allowlisted URL profile; no raw token/private Git field exists. Public-Git submission acknowledges an import session before bounded acquisition completes; status exposes controlled stages, safe terminal errors and activity without command output or host paths. Preview returns snapshot/policy identity, files/indexable bytes, languages, skips/security warnings, enforced limits and duplicates. Confirmation binds the unchanged session snapshot and returns repository/job/version IDs. Cancellation/expiry cleans staging idempotently.

### Repositories, sources and freshness

```text
GET    /repositories
GET    /repositories/{repository_id}
DELETE /repositories/{repository_id}
GET    /repositories/{repository_id}/freshness
POST   /repositories/{repository_id}/sources/sync
```

Sync is public-Git-only in v1 and creates a new immutable source snapshot; it never overwrites citation source. Delete is asynchronous/tombstoned when cleanup may outlive the request and reports audit/cleanup state.

Delete requires `Idempotency-Key` and optional confirmation token supplied by the UI. It always follows tombstone/cancel/fence/drain/cleanup. Response is `202 AsyncRef`. Repository detail exposes lifecycle `active|deleting|deleted`; a deleting repository rejects new work with `409 REPOSITORY_DELETING`.

### Jobs, versions, artifacts and validation

```text
POST /repositories/{repository_id}/index-jobs
GET  /repositories/{repository_id}/index-jobs
GET  /repositories/{repository_id}/index-jobs/{job_id}
POST /repositories/{repository_id}/index-jobs/{job_id}/cancel
GET  /repositories/{repository_id}/index-versions
GET  /repositories/{repository_id}/index-versions/{index_version_id}
GET  /repositories/{repository_id}/index-versions/{index_version_id}/validation-issues
GET  /repositories/{repository_id}/index-versions/{index_version_id}/capabilities
GET  /repositories/{repository_id}/index-versions/{index_version_id}/artifacts
GET  /repositories/{repository_id}/index-versions/{old_id}/diff/{new_id}
```

Pause/resume is absent unless cross-restart semantics are accepted. Artifact listing exposes opaque keys/checksums/metadata only to authorized operator/debug roles, never host paths. Job progress uses server-declared stage codes/labels; frontend does not hard-code a Python pipeline.

### Exploration and ranged source

```text
GET /repositories/{repository_id}/overview
GET /repositories/{repository_id}/files
GET /repositories/{repository_id}/files/{file_key}
GET /repositories/{repository_id}/files/{file_key}/content?start_line=&end_line=
GET /repositories/{repository_id}/symbols
GET /repositories/{repository_id}/symbols/{symbol_key}
GET /repositories/{repository_id}/endpoints
GET /repositories/{repository_id}/endpoints/{endpoint_key}
```

Tree/list endpoints are cursor-paginated. Content requires a bounded line/byte range and returns total lines/bytes, actual range, content hash, encoding policy and truncation. Blocked/secret/binary content is never returned.

### Search and graph

```text
POST /repositories/{repository_id}/search
POST /repositories/{repository_id}/graph/projections
POST /repositories/{repository_id}/graph/paths
POST /repositories/{repository_id}/impact
GET  /repositories/{repository_id}/tests/related
```

Search declares query type, retrievers, filters and final limit; exact mode is deterministic. Results separate candidates from validated evidence. Graph requests declare roots, types, direction, depth and client-requested bounds capped by server policy. Responses return included/available counts or estimates, coverage, unsupported hops, truncation reason and continuation/expand token. Impact groups `direct`, `inferred`, and `unknown`; zero results do not assert zero impact.

### Evidence, claims and assistant

```text
GET  /repositories/{repository_id}/evidence/{evidence_id}
POST /repositories/{repository_id}/evidence/validate
GET  /repositories/{repository_id}/conversations
POST /repositories/{repository_id}/conversations
GET  /repositories/{repository_id}/conversations/{conversation_id}
POST /repositories/{repository_id}/assistant-requests
GET  /repositories/{repository_id}/assistant-requests/{request_id}
GET  /repositories/{repository_id}/agent-traces/{trace_id}
```

Assistant input cannot override server security/evidence/budget maxima. Result separates claims, citations and evidence; includes `answered|limited|insufficient_evidence|cancelled|failed`, searched sources, missing evidence, provider degradation and budget use. Trace is privacy-safe structured events, not chain-of-thought.

### Evaluation and settings

```text
GET  /evaluation/datasets
POST /evaluation/runs
GET  /evaluation/runs/{run_id}
GET  /evaluation/runs/{run_id}/results
GET  /settings
PATCH /settings/preferences
POST /settings/providers/test
```

Evaluation runs bind dataset/fixture/code/index/ranking/workflow/provider/environment identities and retain per-case evidence. Settings expose allowlisted non-secret preferences and configured booleans. No API can disable authorization, source validation, secret filtering, atomic activation, mandatory quotas, evidence validation or release telemetry; provider credential values are never returned.

## Stable status/error codes

OpenAPI owns the enumerations. Minimum families cover authentication/authorization, validation/idempotency, quota/rate, import archive/Git, repository/source/freshness, job lease/cancel/retry, index/artifact/schema/activation, capability/coverage, evidence/citation, provider, dependency readiness and internal correlation. HTTP mapping distinguishes invalid input `400/422`, unauthenticated `401`, forbidden/non-disclosing `403/404`, conflict/idempotency `409`, expired `410`, size/rate `413/429`, dependency `502/503`, timeout `504` and unexpected `500`.

## Verification and compatibility

CI generates/checks OpenAPI, validates examples, detects breaking change, generates/checks frontend types, and runs authorization, pagination/cursor, idempotency/redelivery, explicit-version, range/projection limit, error-envelope/request-ID, insufficient-evidence and provider-degradation contract tests. Breaking changes require version/migration/deprecation and rollback policy; placeholder empty arrays may not impersonate an implemented capability.

`FND-003` generated and drift-tested the first OpenAPI artifact for the current implementation without changing its wire surface. The artifact is the machine-readable regression baseline, not a claim that every semantic target above is implemented. Any field/status divergence is resolved in the owning domain contract first, then this document and OpenAPI change together; application code is not the decision authority by itself.
