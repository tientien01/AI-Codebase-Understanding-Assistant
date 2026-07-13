# PostgreSQL Physical Schema

Status: Accepted implementation design for DAT-002

Authority: Physical table, column, key, constraint, index, and migration-order design

Owner: Data owner

Dependencies: `identity-and-artifact-contract.md`, `specifications/detailed-data-model.md`, `specifications/detailed-storage-design.md`

Related ERD: `postgresql-erd.md`

Last verified: 2026-07-13

This document fixes the production v1 PostgreSQL schema boundary. `DAT-002` may choose SQLAlchemy declaration syntax and Alembic revision identifiers, but it may not rename or weaken these tables, columns, keys, lifecycle checks, or indexes without an owning contract amendment.

## Conventions

- Names use lowercase `snake_case`; tables are plural. Constraint and index names are explicit and stable.
- Opaque IDs are `text`, application-generated, immutable, and checked for the declared prefix. They are never parsed for ownership or ordering.
- Time is `timestamptz` in UTC. Mutable rows have `created_at timestamptz NOT NULL DEFAULT now()` and `updated_at timestamptz NOT NULL DEFAULT now()`; immutable observations omit `updated_at`.
- Lifecycle/state fields are `text` with named `CHECK` constraints. PostgreSQL enum types are not used, so additive state evolution does not require enum DDL outside normal migrations.
- SHA-256 values are lowercase hexadecimal `char(64)` with a format check. Byte/count values are `bigint` with non-negative checks.
- Flexible, non-query-critical metadata is `jsonb NOT NULL DEFAULT '{}'::jsonb`; lists are `jsonb NOT NULL DEFAULT '[]'::jsonb` with object/array type checks. Identity, ownership, lifecycle, lease, source range, retention, and join fields never live only in JSON.
- Canonical keys and normalized relative POSIX paths are `text`; paths reject empty values, absolute prefixes, backslashes, NUL, and `..` segments. Host absolute paths are forbidden.
- All foreign keys name their deletion action. Repository-owned operational rows normally cascade from the repository; retained evidence, audit, and evaluation links use `RESTRICT` or nullable `SET NULL` as specified.
- All mutable rows use application-set `updated_at`; a shared trigger may enforce timestamp updates but is not schema authority.

Column lists below use `!` for `NOT NULL`, `?` for nullable, and `=` for a database default. All primary-key columns are `!`.

## Lifecycle checks

| Constraint | Allowed values |
| --- | --- |
| `ck_repositories_lifecycle` | `active`, `deleting`, `deleted` |
| `ck_repository_recovery_state` | `ready`, `blocked` |
| `ck_repository_sources_type` | `upload_zip`, `upload_folder`, `public_git` |
| `ck_import_sessions_state` | `created`, `acquiring`, `scanning`, `preview_ready`, `confirming`, `confirmed`, `cancelled`, `expired`, `failed` |
| `ck_index_jobs_state` | `queued`, `running`, `succeeded`, `succeeded_with_warnings`, `failed`, `cancelled` |
| `ck_job_attempts_state` | `claimed`, `running`, `succeeded`, `failed`, `cancelled`, `lease_lost` |
| `ck_index_versions_lifecycle` | `building`, `validating`, `ready`, `ready_with_warnings`, `active`, `superseded`, `expired`, `failed`, `cancelled` |
| `ck_build_kind` | `full`, `incremental` |
| `ck_capability_state` | `ready`, `limited`, `unavailable`, `failed`, `stale` |
| `ck_source_freshness` | `fresh`, `possibly_stale`, `stale`, `source_missing`, `unverifiable` |
| `ck_support_type` | `source_exact`, `static_resolved`, `static_ambiguous`, `heuristic_inferred`, `llm_inferred`, `user_supplied` |
| `ck_reference_outcome` | `resolved`, `ambiguous`, `unresolved` |
| `ck_evidence_freshness` | `fresh`, `stale`, `invalid` |
| `ck_message_role` | `operator`, `assistant`, `system` |
| `ck_assistant_outcome` | `answered`, `limited`, `insufficient_evidence`, `cancelled`, `failed` |
| `ck_deletion_state` | `queued`, `running`, `partially_failed`, `succeeded`, `failed` |

## Access, idempotency, deletion, and audit

### `operator_principals`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `principal_` |
| `display_name` | `text!` |
| `status` | `text! = 'active'`, check `active|disabled` |
| `created_at`, `updated_at` | shared mutable timestamps |

### `operator_sessions`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `session_` |
| `principal_id` | `text!`, FK principals `CASCADE` |
| `token_hash` | `text!`, unique; one-way session-token hash only |
| `csrf_secret_hash` | `text!`, one-way hash only |
| `expires_at`, `last_seen_at`, `revoked_at` | `timestamptz!`, `timestamptz?`, `timestamptz?` |
| `created_at` | shared immutable timestamp |

### `operator_api_tokens`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `token_` |
| `principal_id` | `text!`, FK principals `CASCADE` |
| `name` | `text!` |
| `token_hash` | `text!`, unique; raw token is never stored |
| `last_used_at`, `expires_at`, `revoked_at` | `timestamptz?` |
| `created_at` | shared immutable timestamp |

### `idempotency_records`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `idem_` |
| `principal_id` | `text!`, FK principals `RESTRICT` |
| `operation` | `text!` |
| `idempotency_key` | `text!` |
| `normalized_request_hash` | `char(64)!` |
| `state` | `text!`, check `in_progress|completed|failed` |
| `http_status` | `smallint?`, check `100..599` |
| `resource_type`, `resource_id` | `text?`, `text?`, both-null-or-both-present check |
| `response_ref` | `text?`, opaque artifact/cache key, never raw secret response |
| `expires_at`, `created_at`, `updated_at` | `timestamptz!`, shared timestamps |

Unique `uq_idempotency_scope(principal_id, operation, idempotency_key)` enforces retry identity. Request-hash comparison is transactional; a different hash returns `IDEMPOTENCY_CONFLICT`.

### `audit_events`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `audit_` |
| `principal_id` | `text?`, FK principals `SET NULL` |
| `repository_id` | `text?`, FK repositories `SET NULL` |
| `request_id`, `event_type`, `outcome` | `text?`, `text!`, `text!` |
| `resource_type`, `resource_id` | `text?`, `text?` |
| `details` | `jsonb! = {}`, privacy-safe structured metadata |
| `created_at` | shared immutable timestamp |

Audit rows are append-only. Application roles receive no update/delete grant.

### `repository_deletion_operations`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `delete_` |
| `repository_id` | `text!`, FK repositories `RESTRICT` |
| `idempotency_record_id` | `text!`, unique FK idempotency records `RESTRICT` |
| `state` | `text! = 'queued'`, `ck_deletion_state` |
| `repository_generation` | `bigint!`, non-negative fencing generation |
| `attempt_count` | `integer! = 0`, non-negative |
| `last_error_code` | `text?` |
| `cleanup_summary` | `jsonb! = {}` |
| `started_at`, `finished_at` | `timestamptz?` |
| `created_at`, `updated_at` | shared mutable timestamps |

Only one unfinished deletion is allowed by `uq_deletion_one_active(repository_id) WHERE state IN ('queued','running','partially_failed')`.

## Repository, source, and import

### `repositories`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `repo_` |
| `owner_principal_id` | `text!`, FK principals `RESTRICT` |
| `display_name` | `text!` |
| `lifecycle` | `text! = 'active'`, `ck_repositories_lifecycle` |
| `recovery_state` | `text! = 'ready'`, `ck_repository_recovery_state`; storage-contract `recovery_blocked` maps to `blocked` without changing lifecycle |
| `active_index_version_id` | `text?`, deferred composite FK `(id, active_index_version_id)` to index versions |
| `source_freshness` | `text! = 'unverifiable'`, `ck_source_freshness` |
| `operation_generation` | `bigint! = 0`, non-negative fencing generation |
| `deletion_requested_at`, `deleted_at` | `timestamptz?` |
| `created_at`, `updated_at` | shared mutable timestamps |

Unique `(id, owner_principal_id)` supports ownership FKs. A deferred constraint trigger verifies that a non-null active version has lifecycle `active`; lifecycle `deleted` requires `active_index_version_id IS NULL` and `deleted_at IS NOT NULL`.

### `repository_sources`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `source_` |
| `repository_id` | `text!`, FK repositories `CASCADE` |
| `source_type` | `text!`, `ck_repository_sources_type` |
| `canonical_locator` | `text?`, normalized public locator; null for uploads |
| `credential_ref` | `text?`, opaque secret-manager reference only |
| `default_ref`, `last_synchronized_revision` | `text?` |
| `source_fingerprint` | `char(64)?` |
| `created_at`, `updated_at` | shared mutable timestamps |

Unique `(repository_id, id)` supports snapshot ownership. `uq_repository_source_locator(repository_id, source_type, canonical_locator)` applies when the locator is non-null.

### `source_snapshots`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `snapshot_` |
| `repository_id`, `repository_source_id` | `text!`, composite FK to repository sources `CASCADE` |
| `revision` | `text?` |
| `storage_key` | `text!`, opaque repository-owned key |
| `snapshot_sha256` | `char(64)!` |
| `policy_version`, `inventory_schema_version` | `text!` |
| `total_files`, `total_bytes` | `bigint!`, non-negative |
| `created_at` | shared immutable timestamp |

Unique `(repository_id, id)` and unique `(repository_id, repository_source_id, snapshot_sha256)` prevent duplicate immutable snapshots.

### `import_sessions`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `import_` |
| `principal_id` | `text!`, FK principals `RESTRICT` |
| `source_type` | `text!`, `ck_repository_sources_type` |
| `state` | `text! = 'created'`, `ck_import_sessions_state` |
| `staging_key`, `preview_artifact_key` | `text?`, opaque temporary keys |
| `policy_version` | `text!` |
| `source_fingerprint` | `char(64)?` |
| `upload_bytes`, `indexable_bytes`, `total_files`, `indexable_files` | `bigint! = 0`, non-negative |
| `warnings`, `duplicate_candidates`, `limits` | `jsonb!`, first two default `[]`, limits defaults `{}`, with array/object type checks |
| `confirmed_repository_id`, `confirmed_snapshot_id` | `text?`, deferred composite FK to source snapshots; both-null-or-both-present |
| `expires_at` | `timestamptz!` |
| `confirmed_at`, `cancelled_at`, `failed_at` | `timestamptz?` |
| `created_at`, `updated_at` | shared mutable timestamps |

Indexes support `(state, expires_at, id)` cleanup and `(principal_id, created_at DESC, id DESC)` history.

## Durable jobs, attempts, versions, and artifacts

### `index_jobs`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `job_` |
| `repository_id` | `text!`, FK repositories `CASCADE` |
| `source_snapshot_id` | `text!`, composite FK to snapshots `RESTRICT` |
| `requested_build_kind`, `effective_build_kind` | `text!`, `ck_build_kind` |
| `base_index_version_id`, `target_index_version_id` | `text?`, composite FKs to versions `RESTRICT`; target becomes non-null during preflight before stage writes |
| `state` | `text! = 'queued'`, `ck_index_jobs_state` |
| `priority` | `smallint! = 0` |
| `idempotency_record_id` | `text!`, unique FK idempotency records `RESTRICT` |
| `current_attempt_id` | `text?`, deferred composite FK to job attempts |
| `lease_generation` | `bigint! = 0`, non-negative fencing token |
| `repository_generation` | `bigint!`, captured repository fencing generation |
| `stage_code` | `text! = 'queued'` |
| `progress_completed`, `progress_total` | `bigint?`, both-null-or-both-present and non-negative |
| `progress_unit` | `text?`, present iff progress values are present |
| `cancellation_requested_at` | `timestamptz?` |
| `warning_count` | `integer! = 0`, non-negative |
| `error_code`, `error_message_safe` | `text?` |
| `queued_at` | `timestamptz! = now()` |
| `started_at`, `finished_at` | `timestamptz?` |
| `created_at`, `updated_at` | shared mutable timestamps |

`uq_index_jobs_one_active(repository_id) WHERE state IN ('queued','running')` implements the production v1 reject policy. State/timestamp checks require running jobs to have `started_at`, terminal jobs to have `finished_at`, and succeeded jobs to have a target version.
Unique `(repository_id, id)` supports attempt and ownership FKs.

### `job_attempts`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `attempt_` |
| `job_id`, `repository_id` | `text!`, composite FK to index jobs `CASCADE` |
| `lease_generation` | `bigint!`, positive; unique per job |
| `worker_id` | `text!`, opaque worker identity |
| `state` | `text! = 'claimed'`, `ck_job_attempts_state` |
| `lease_expires_at`, `heartbeat_at` | `timestamptz!` |
| `checkpoint_stage` | `text?` |
| `checkpoint_artifact_id` | `text?`, FK artifacts `SET NULL` |
| `error_code`, `error_message_safe` | `text?` |
| `claimed_at` | `timestamptz! = now()` |
| `finished_at` | `timestamptz?` |

Unique `(job_id, id)`, `(repository_id, job_id, id)`, and `(job_id, lease_generation)` support fencing. Conditional worker writes compare job, attempt, generation, job state, lease expiry, repository generation, and cancellation.

### `index_versions`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `idx_` |
| `repository_id` | `text!`, FK repositories `CASCADE` |
| `version_number` | `bigint!`, positive display/order value |
| `source_snapshot_id` | `text!`, composite FK to snapshots `RESTRICT` |
| `base_index_version_id` | `text?`, composite self-FK `RESTRICT` |
| `build_kind` | `text!`, `ck_build_kind` |
| `lifecycle` | `text! = 'building'`, `ck_index_versions_lifecycle` |
| `manifest_schema_version`, `producer_version`, `configuration_sha256` | `text!`, `text!`, `char(64)!` |
| `manifest_storage_key`, `manifest_sha256` | `text?`, `char(64)?`, both-null-or-both-present |
| `validation_status` | `text?`, check `passed|passed_with_warnings|failed` |
| `critical_issue_count` | `integer! = 0`, non-negative |
| `coverage` | `jsonb! = {}` |
| `started_at` | `timestamptz! = now()` |
| `finished_at`, `activated_at`, `superseded_at`, `expired_at` | `timestamptz?` |
| `created_at` | shared immutable timestamp |

Unique `(repository_id, id)` and `(repository_id, version_number)` are mandatory. `uq_index_versions_one_active(repository_id) WHERE lifecycle = 'active'` enforces one active version. Ready/active states require finalized manifest identity and a finished timestamp; active requires `activated_at`.

### `index_artifacts`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `artifact_` |
| `repository_id`, `index_version_id` | `text!`, composite FK to versions `CASCADE` |
| `artifact_type`, `storage_key`, `schema_version` | `text!` |
| `sha256` | `char(64)!` |
| `byte_size`, `record_count` | `bigint!`, non-negative |
| `producer_stage`, `producer_name`, `producer_version` | `text!` |
| `required` | `boolean! = false` |
| `retention_class` | `text!`, check `active_required|retained_previous_evidence|evaluation_audit|failed_build_diagnostic|temporary_debug` |
| `finalized_at` | `timestamptz!` |
| `created_at` | shared immutable timestamp |

Unique `(repository_id, index_version_id, id)`, `(repository_id, index_version_id, artifact_type, storage_key)`, and storage key prevent ambiguous manifests.

### `validation_issues`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `issue_` |
| `repository_id`, `index_version_id` | `text!`, composite FK to versions `CASCADE` |
| `code`, `severity` | `text!`, severity check `info|warning|error|critical` |
| `entity_type`, `entity_key`, `file_key` | `text?` |
| `start_line`, `end_line` | `integer?`, valid paired inclusive range |
| `message_safe` | `text!` |
| `details` | `jsonb! = {}` |
| `created_at` | shared immutable timestamp |

### `capability_readiness`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `capability_` |
| `repository_id`, `index_version_id` | `text!`, composite FK to versions `CASCADE` |
| `capability` | `text!` |
| `state` | `text!`, `ck_capability_state` |
| `reason_codes`, `required_artifact_types` | `jsonb! = []`, array checks |
| `validation_issue_id` | `text?`, FK validation issues `SET NULL` |
| `coverage`, `remediation` | `jsonb! = {}`, `text?` |
| `created_at`, `updated_at` | shared mutable timestamps |

Unique `(repository_id, index_version_id, capability)` prevents conflicting readiness.

## Versioned code intelligence and graph

Every table in this section has composite FK `(repository_id, index_version_id)` to `index_versions`, immutable `created_at`, and a unique `(repository_id, index_version_id, canonical_key)` unless stated otherwise. Producer fields are `producer_stage text!`, `producer_name text!`, `producer_version text!`; support fields are `support_type text!`, `confidence double precision?`, and `diagnostic_ids jsonb! = []`. Confidence is null for exact facts unless explicitly required and is constrained to `0..1` when present.

### `files`

`id text!` prefix `fileobs_`; `canonical_key text!`; `relative_path text!`; `language text!`; `file_type text!`; `byte_size bigint!`; `content_sha256 char(64)!`; `encoding text!`; `parse_status text!`; producer fields. Unique normalized path per version. No host absolute path or full content column.

### `symbols`

`id text!` prefix `symbolobs_`; `canonical_key text!`; `file_id text!` same-version composite FK to files; `name text!`; `qualified_name text!`; `symbol_kind text!`; `signature text?`; `start_line integer!`; `end_line integer!`; producer/support fields. Range is inclusive and positive.

### `endpoints`

`id text!` prefix `endpointobs_`; `canonical_key text!`; `file_id text!` same-version FK; `handler_symbol_id text?` same-version FK; `protocol text!`; `method text!`; `normalized_route text!`; `start_line integer!`; `end_line integer!`; producer/support fields. Unique `(repository_id, index_version_id, protocol, method, normalized_route, handler_symbol_id)`.

### `references`

`id text!` prefix `reference_`; `canonical_key text!`; `source_file_id text!` same-version FK; `source_symbol_id text?` same-version FK; `target_entity_type text?`; `target_canonical_key text?`; `reference_type text!`; `outcome text!` with `ck_reference_outcome`; `start_line integer!`; `end_line integer!`; `candidate_keys jsonb! = []`; producer/support fields. Resolved requires one target key; unresolved forbids it; ambiguous requires at least two candidate keys.

### `chunks`

`id text!` prefix `chunkobs_`; `canonical_key text!`; `source_entity_type text!`; `source_canonical_key text!`; `file_id text!` same-version FK; `chunk_kind text!`; `ordinal integer!` non-negative; `start_line integer!`; `end_line integer!`; `content_sha256 char(64)!`; `safe_preview text!`; `artifact_id text?` same-version artifact FK; `artifact_offset bigint?`; `artifact_length bigint?`; `retrieval_metadata jsonb! = {}`; producer fields. Payload location fields are all-null or all-present.

### `graph_candidates`

`id text!` prefix `candidate_`; `candidate_kind text!` check `node|edge`; `canonical_key text!`; `source_canonical_key text?`; `target_canonical_key text?`; `relation_type text?`; `origin text!`; `file_id text?` same-version FK; `start_line integer?`; `end_line integer?`; `status text!` check `pending|accepted|changed|dropped`; `normalization_reason text?`; producer/support fields. Edge candidates require source, target, and relation; node candidates forbid target.

### `graph_nodes`

`id text!` prefix `nodeobs_`; `canonical_key text!`; `node_type text!`; `label text!`; `file_id text?` same-version FK; `entity_canonical_key text?`; `start_line integer?`; `end_line integer?`; `coverage_state text!`; `metadata jsonb! = {}`; producer/support fields. Unique `(repository_id, index_version_id, id)` supports edge FKs.

### `graph_edges`

`id text!` prefix `edgeobs_`; `canonical_key text!`; `source_node_id text!`; `target_node_id text!`; `edge_type text!`; `file_id text?`; `start_line integer?`; `end_line integer?`; `weight double precision?`; `metadata jsonb! = {}`; producer/support fields. Composite FKs `(repository_id, index_version_id, source_node_id|target_node_id)` guarantee same-version nodes. Source and target may be equal only for edge types explicitly allowed by the graph schema.

## Evidence and assistant

### `evidence`

| Column | Type and rule |
| --- | --- |
| `id` | `text!`, PK, prefix `evidence_` |
| `repository_id`, `index_version_id` | `text!`, composite FK to versions `RESTRICT` |
| `source_entity_type`, `source_canonical_key` | `text!` |
| `file_id` | `text?`, same-version composite FK to files `RESTRICT` |
| `start_line`, `end_line` | `integer?`, both null for file-level evidence or valid paired inclusive range |
| `content_sha256` | `char(64)!` |
| `support_type` | `text!`, `ck_support_type` |
| `producer_stage`, `producer_name`, `producer_version` | `text!` |
| `retrieval_source`, `selection_reason` | `text!` |
| `freshness` | `text! = 'fresh'`, `ck_evidence_freshness` |
| `safe_preview` | `text!` |
| `validation_details` | `jsonb! = {}` |
| `created_at`, `staled_at` | `timestamptz! = now()`, `timestamptz?` |

Unique `(repository_id, index_version_id, id)` supports citations. Evidence is retained with `RESTRICT` FKs; cleanup must prove it is unreferenced or policy-expired.

### `conversations`

`id text!` prefix `conversation_`; `principal_id text!` FK principals `RESTRICT`; `repository_id text!` FK repositories `RESTRICT`; `title text?`; `status text! = 'active'` check `active|archived|deleted`; `created_at`, `updated_at`. Index ownership and recent ordering.

### `messages`

`id text!` prefix `message_`; `conversation_id text!` FK conversations `CASCADE`; `repository_id text!` FK repositories `RESTRICT`; `index_version_id text?` composite FK versions `RESTRICT`; `role text!` with `ck_message_role`; `content text!`; `assistant_outcome text?` with `ck_assistant_outcome`; `request_id text?`; `created_at`. Unique `(conversation_id, id)` and `(repository_id, index_version_id, id)` support claim ownership; ordered index `(conversation_id, created_at, id)` provides stable pagination.

### `claims`

`id text!` prefix `claim_`; `message_id text!` FK messages `CASCADE`; `repository_id text!`; `index_version_id text!`; `claim_text text!`; `support_level text!` check `supported|qualified|unsupported`; `ordinal integer!` non-negative; `created_at`. Composite ownership FK `(repository_id, index_version_id, message_id)` binds the message repository/version. Unique `(repository_id, index_version_id, id)` and `(message_id, ordinal)`.

### `citations`

`id text!` prefix `citation_`; `claim_id text!`; `evidence_id text!`; `repository_id text!`; `index_version_id text!`; `display_locator text!`; `created_at`. Composite FKs `(repository_id, index_version_id, claim_id)` and `(repository_id, index_version_id, evidence_id)` guarantee claim/evidence scope and version equality. Unique `(claim_id, evidence_id)`.

### `agent_traces`

`id text!` prefix `trace_`; `principal_id text!` FK principals `RESTRICT`; `repository_id text!`; `index_version_id text?`; `conversation_id text?`; `request_message_id text?`; `response_message_id text?`; `workflow_version text!`; `outcome text!` with `ck_assistant_outcome`; `budget_summary jsonb! = {}`; `provider_summary jsonb! = {}`; `started_at timestamptz!`; `finished_at timestamptz?`; `created_at`. No prompt dump or hidden reasoning column.

### `agent_trace_events`

`id text!` prefix `traceevent_`; `trace_id text!` FK traces `CASCADE`; `sequence integer!` positive; `event_type text!`; `tool_name text?`; `status text!`; `duration_ms bigint?` non-negative; `payload jsonb! = {}` privacy-safe structured fields; `created_at`. Unique `(trace_id, sequence)`.

## Evaluation

### `evaluation_datasets`

`id text!` prefix `dataset_`; `name text!`; `version text!`; `schema_version text!`; `description text?`; `artifact_storage_key text!`; `artifact_sha256 char(64)!`; `status text!` check `draft|frozen|retired`; `created_at`. Unique `(name, version)`.

### `evaluation_cases`

`id text!` prefix `evalcase_`; `dataset_id text!` FK datasets `CASCADE`; `case_key text!`; `question text!`; `ground_truth jsonb! = {}`; `expected_evidence jsonb! = []`; `tags jsonb! = []`; `ordinal integer!`; `created_at`. Unique `(dataset_id, case_key)` and `(dataset_id, ordinal)`.

### `evaluation_runs`

`id text!` prefix `evalrun_`; `dataset_id text!` FK datasets `RESTRICT`; `repository_id text?` FK repositories `SET NULL`; `index_version_id text?` composite FK versions `RESTRICT`; `method text!`; `configuration_sha256 char(64)!`; `code_revision text!`; `ranking_version text?`; `workflow_version text?`; `provider_identity jsonb! = {}`; `environment_identity jsonb! = {}`; `state text!` check `queued|running|succeeded|failed|cancelled`; `started_at timestamptz?`; `finished_at timestamptz?`; `created_at`. Repository and index are both null or both present.

### `evaluation_results`

`id text!` prefix `evalresult_`; `run_id text!` FK runs `CASCADE`; `case_id text!` FK cases `RESTRICT`; `trace_id text?` FK traces `SET NULL`; `answer text?`; `outcome text!`; `retrieved_evidence jsonb! = []`; `citations jsonb! = []`; `automatic_metrics jsonb! = {}`; `manual_scores jsonb! = {}`; `duration_ms bigint?`; `created_at`. Unique `(run_id, case_id)`.

## Foreign-key and ownership rules

1. All versioned observations reference `index_versions(repository_id, id)` with the same repository ID.
2. File, symbol, endpoint, reference, chunk, graph, and evidence sub-relations use composite repository/version FKs; a plain entity ID FK is insufficient.
3. `repositories.active_index_version_id` and `index_jobs.current_attempt_id` are deferred cyclic FKs added after both sides exist.
4. Graph edge source and target FKs include repository and index version, making cross-version edges impossible.
5. Evidence-to-file, citation-to-evidence, and claim/message ownership FKs include repository and index version. Historical evidence prevents accidental version deletion.
6. Audit principal/repository references use `SET NULL` so security history survives account or repository cleanup. IDs also remain in privacy-safe details only when policy permits.
7. Evaluation references use `RESTRICT` for frozen datasets/cases and index versions used as release evidence.

## Access patterns and named indexes

| Index | Columns/predicate | Consumer |
| --- | --- | --- |
| `ix_repositories_owner_list` | `(owner_principal_id, created_at DESC, id DESC)` | repository cursor list |
| `ix_repositories_lifecycle` | `(lifecycle, updated_at, id)` | deletion/recovery operations |
| `ix_import_sessions_expiry` | `(state, expires_at, id)` for non-terminal states | TTL cleanup |
| `ix_index_jobs_recovery` | `(state, updated_at, id)` where queued/running | dispatcher and recovery scan |
| `ix_index_jobs_repository_history` | `(repository_id, created_at DESC, id DESC)` | job history/status API |
| `ix_job_attempts_stale_lease` | `(state, lease_expires_at, id)` where claimed/running | stale lease recovery |
| `ix_index_versions_repository_history` | `(repository_id, version_number DESC, id)` | version history and activation comparison |
| `ix_index_artifacts_manifest` | `(repository_id, index_version_id, artifact_type, id)` | manifest validation/listing |
| `ix_validation_issues_version_severity` | `(repository_id, index_version_id, severity, id)` | validation/capability gates |
| `ix_files_path` | `(repository_id, index_version_id, relative_path, id)` | exact file lookup/tree |
| `ix_symbols_name` | `(repository_id, index_version_id, name, canonical_key, id)` | symbol search/pagination |
| `ix_endpoints_route` | `(repository_id, index_version_id, protocol, method, normalized_route, id)` | endpoint lookup/list |
| `ix_references_source` | `(repository_id, index_version_id, source_canonical_key, reference_type, id)` | forward reference traversal |
| `ix_references_target` | `(repository_id, index_version_id, target_canonical_key, reference_type, id)` | reverse impact traversal |
| `ix_chunks_source` | `(repository_id, index_version_id, source_canonical_key, ordinal, id)` | source chunk range |
| `ix_graph_edges_forward` | `(repository_id, index_version_id, source_node_id, edge_type, target_node_id, id)` | bounded forward traversal |
| `ix_graph_edges_reverse` | `(repository_id, index_version_id, target_node_id, edge_type, source_node_id, id)` | bounded reverse traversal |
| `ix_evidence_source` | `(repository_id, index_version_id, source_canonical_key, created_at DESC, id)` | evidence lookup/validation |
| `ix_conversations_recent` | `(principal_id, repository_id, updated_at DESC, id DESC)` | conversation list |
| `ix_messages_order` | `(conversation_id, created_at, id)` | stable message pagination |
| `ix_trace_events_order` | `(trace_id, sequence, id)` | trace reconstruction |
| `ix_evaluation_runs_recent` | `(dataset_id, created_at DESC, id DESC)` | run history |
| `ix_evaluation_results_run` | `(run_id, case_id, id)` | per-run evaluation results |
| `ix_audit_events_resource` | `(resource_type, resource_id, created_at DESC, id DESC)` | operator audit lookup |

Every foreign-key child prefix also receives an index unless one of the named indexes above already has that prefix. DAT-002 records the mapping and must not create a duplicate equivalent index.

Text/trigram, vector, lexical, and full-text indexes are not selected by DAT-001. They require measured query plans and technology adoption evidence. Exact canonical and B-tree access remains mandatory.

## Transaction boundaries

### Import confirmation

Lock the import session, verify `preview_ready`, expiry, policy and fingerprint, then create repository, source, immutable snapshot, optional first index version/job, idempotency outcome, and audit event in one transaction. Storage publication finalizes before commit or is compensated on rollback. Confirmation updates the session to `confirmed` exactly once.

### Job claim and heartbeat

Claim uses one conditional transaction: lock the queued job, verify repository lifecycle/generation and cancellation, increment `lease_generation`, insert the attempt, set `current_attempt_id`, transition to running, and record lease times. Heartbeat/checkpoint/terminal updates predicate on job ID, attempt ID, generation, running state, unexpired lease, repository generation, and cancellation boundary.

### Index activation

Lock repository, job, candidate version, and expected previous active version. Verify the current attempt fencing predicate, ready manifest/checksums, zero critical issues, mandatory readiness, source ownership, cancellation, and expected previous version. In one deferred-constraint transaction, mark the candidate active, previous active superseded, update the repository pointer, stale affected evidence, complete the job, and append audit. Any failure leaves the previous pointer and lifecycle unchanged.

### Repository deletion

Submission locks the repository, changes lifecycle to deleting, increments operation generation, requests cancellation on non-terminal jobs, inserts/reuses one deletion operation through idempotency, and appends audit. Cleanup waits for terminal jobs/expired leases, enumerates only owned rows/manifest keys, records partial failures, and marks deleted only after validation.

## DAT-002 migration order

1. Create shared check helpers only where PostgreSQL cannot express a named inline check; do not create PostgreSQL enum types.
2. Create access tables: principals, sessions, API tokens, and idempotency records.
3. Create repositories without the active-version FK; create sources, snapshots, and import sessions.
4. Create index versions without repository active pointer; create jobs without current-attempt FK; create artifacts and attempts.
5. Add deferred cyclic FKs for repository active version, job current attempt, and import confirmation snapshot.
6. Create validation/readiness, code intelligence, graph, evidence/assistant, evaluation, deletion, and audit tables in FK order.
7. Create partial unique indexes, access-pattern indexes, deferred active-lifecycle constraint trigger, and append-only audit protections.
8. Add only non-secret deterministic seed/config rows if an accepted task requires them; DAT-002 otherwise seeds nothing.
9. Run empty upgrade, supported SQLite-to-production data mapping fixture, constraint/FK/index inspection, schema drift, and forward-recovery tests declared by DAT-002.

SQLite remains a local/test compatibility profile. It may emulate partial indexes and checks where supported, but it does not define production DDL. Existing integer `index_version` values and absolute source paths require explicit mapping to opaque index/source snapshot records; they must not be copied as production identity.
