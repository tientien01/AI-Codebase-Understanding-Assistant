# Error Handling and Fallback Contract

Status: Accepted production v1 specification  
Authority: Failure outcome, retry, fallback, cleanup, and UI semantics; HTTP wire shape/codes are owned by OpenAPI and the API contract  
Owner: Reliability and API owners  
Dependencies: `../README.md`, `../../02-system-architecture/failure-model.md`, `../../06-api-and-integrations/specifications/detailed-rest-api-contract.md`  
Related source: `../../14-implementation-baseline/api-coverage.md`  
Related tests: error-envelope, dependency fault, degraded-capability, retry, cleanup, and UI-state suites  
Last verified: 2026-07-12

## Universal rules

- Use the API contract's single error envelope with stable code, safe message, schema-defined details, request ID, retryability and optional retry-after.
- Do not expose stack traces, credentials, host paths, unrestricted source/provider payloads, existence of unauthorized repositories, or internal lease owners.
- Retryability is declared by the server. Clients never infer it from prose or status alone.
- Expected product outcomes such as `limited`, `stale`, truncated projection and `insufficient_evidence` are successful typed results, not generic exceptions.
- Cleanup is idempotent, repository/session/version scoped and never follows untrusted paths.
- A partial result is returned only when the owning capability defines a safe state with coverage, truncation, diagnostics and remediation.

## Failure classes

| Class | Retry policy | Required containment |
| --- | --- | --- |
| Invalid/security input | Non-retryable until input changes | Reject before publication/expensive work; cleanup staging |
| Conflict/idempotency | Non-retryable as submitted | Return existing operation or conflict details without duplicate effect |
| Transient dependency | Retryable with bounded backoff/jitter and server hint | Preserve authoritative state; no guessed transition |
| Permanent dependency/config | Non-retryable until operator remediation | Mark dependent capability unavailable/failed; keep deterministic paths |
| File-scoped parse | Not automatically retried unless component/input changes | Record diagnostic; calculate capability coverage |
| Candidate index fatal | Retry only through a new/recovered attempt policy | Keep candidate inactive and prior active version unchanged |
| Evidence/claim invalid | Repair once within budget or return insufficient | Never render invalid citation as support |
| Restore inconsistency | Operator-retryable only | Keep service/repository unready until a valid consistency set exists |

## Canonical behavior matrix

| Condition | Authoritative state | Behavior and user-visible result |
| --- | --- | --- |
| Upload interrupted | Temporary upload token, no published session | Delete by TTL; user restarts upload; production v1 has no resumable upload |
| Import expired/changed | Import session/snapshot fingerprint | `410 IMPORT_SESSION_EXPIRED` or changed-session conflict; rescan/review before confirm |
| Unsafe archive/Git | Rejected import diagnostic | Non-retryable safe error; quarantine/cleanup; no repository/index created |
| Duplicate confirm/index submission | Idempotency record/job | Same request returns original result; different hash conflicts |
| Second incompatible index | Existing running job | `409 INDEX_ALREADY_RUNNING` with current job; do not enqueue silently |
| Lease lost/stale worker | Attempt + lease generation | Conditional writes fail `LEASE_LOST`; worker stops; no publish |
| Cancellation before activation | Persistent cancellation flag | Stop at safe boundary; candidate cancelled; prior active remains |
| Cancellation after activation commit | Active version/audit | `409 CANCELLATION_TOO_LATE`; successful activation remains authoritative |
| Redis outage | PostgreSQL job state | New delivery deferred/rejected with retry hint; running fenced work follows DB state; reconcile after recovery |
| PostgreSQL outage | PostgreSQL | API/workers unready; stop authoritative transitions; retry after readiness |
| Artifact outage/disk full/checksum mismatch | Manifest/version state | Stop write/read/publish, quarantine incomplete/corrupt output, preserve active version |
| One file parse failure | Diagnostic artifact | Continue only with capability-scoped limited coverage |
| Whole language profile failure | Profile validation/readiness | Parser-dependent capabilities failed; safe file/lexical capability may remain; mandatory-plan failure blocks activation |
| Excess unresolved references | Resolution diagnostics/coverage | Never hide/drop; critical integrity failures block, otherwise graph/flow/impact limited |
| Semantic/vector failure | Semantic artifact/capability | Deterministic exact/lexical/metadata/graph remain; semantic not ready |
| LLM failure | Provider trace/capability | Deterministic template only when faithful; otherwise limited provider-unavailable result |
| Oversized graph/query | Projection budget | Successful bounded result with coverage/truncation/continuation |
| Stale evidence | Evidence/index IDs | Preserve inspectability, mark stale and offer current re-run |
| Invalid citation/range/hash | Evidence validation | Exclude from support; bounded answer repair or insufficient evidence |
| Delete with running job | Repository/job/generation | Tombstone, cancel, fence, drain, cleanup; reject new work; remain deleting on partial failure |
| Restore missing artifact | Backup/manifest/readiness | Remain unready; restore matching set, validated older activation, or new rebuild; otherwise recovery-blocked |
| Prompt injection | Security policy/tool allowlist | Treat source as data; ignore instruction; never expand tools/permissions |
| Secret in allowed example/config | Content security decision | Redact/quarantine the detected value before any sink; file may expose only validated variable names |
| Cross-repository access | Principal/ownership | Non-disclosing not-found response plus safe audit event |

## Capability mapping

Capability results use only `ready`, `limited`, `unavailable`, `failed`, or `stale`. Build/job/repository/source states remain separate. An optional failure may not collapse unrelated ready capabilities into repository failure. API and UI always include reason codes, validation reference where applicable, coverage/truncation, retryability and remediation.

## Required evidence

Each production-critical row maps to an automated test or exercised drill: adversarial import, idempotency, redelivery/fencing, worker kill, cancel-before/after activation, broker/DB/artifact/disk faults, parser/profile/resolver coverage, provider degradation, graph limits, stale/invalid evidence, delete race, prompt injection, authorization and incomplete restore. Release evidence records exact candidate, configuration, fixture/environment, command, result and immutable artifact/checksum.
