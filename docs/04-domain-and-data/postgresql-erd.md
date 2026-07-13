# PostgreSQL Entity-Relationship Design

Status: Accepted implementation design for DAT-002

Authority: Production v1 table relationships and aggregate ownership

Owner: Data owner

Detailed columns and constraints: `postgresql-physical-schema.md`

Last verified: 2026-07-13

The diagrams are split by aggregate so keys remain readable. Repeated boundary tables such as `repositories` and `index_versions` represent the same physical table. Composite lines labeled by the surrounding text always include repository and index-version ownership; a single ID arrow must not be implemented when the physical schema requires a composite foreign key.

## Access, repository, source, and import

```mermaid
erDiagram
    operator_principals ||--o{ operator_sessions : authenticates
    operator_principals ||--o{ operator_api_tokens : owns
    operator_principals ||--o{ idempotency_records : scopes
    operator_principals ||--o{ repositories : owns
    operator_principals ||--o{ import_sessions : initiates
    operator_principals o|--o{ audit_events : acts

    repositories ||--o{ repository_sources : acquires_from
    repository_sources ||--o{ source_snapshots : publishes
    import_sessions o|--o| source_snapshots : confirms_as
    repositories ||--o{ repository_deletion_operations : deletes
    idempotency_records ||--o| repository_deletion_operations : deduplicates
    repositories o|--o{ audit_events : records

    operator_principals {
      text id PK
      text status
    }
    operator_sessions {
      text id PK
      text principal_id FK
      text token_hash UK
    }
    operator_api_tokens {
      text id PK
      text principal_id FK
      text token_hash UK
    }
    idempotency_records {
      text id PK
      text principal_id FK
      text operation
      text idempotency_key
    }
    repositories {
      text id PK
      text owner_principal_id FK
      text active_index_version_id FK
      bigint operation_generation
    }
    repository_sources {
      text id PK
      text repository_id FK
      text source_type
    }
    source_snapshots {
      text id PK
      text repository_id FK
      text repository_source_id FK
      char snapshot_sha256
    }
    import_sessions {
      text id PK
      text principal_id FK
      text confirmed_repository_id FK
      text confirmed_snapshot_id FK
    }
    repository_deletion_operations {
      text id PK
      text repository_id FK
      text idempotency_record_id FK
    }
    audit_events {
      text id PK
      text principal_id FK
      text repository_id FK
    }
```

`import_sessions` owns temporary acquisition state and may point to the immutable repository snapshot only after confirmation. A repository never points back to an import session. Audit relationships are nullable and use `SET NULL`; deletion operations retain the repository FK until validated cleanup completes.

## Durable job and index lifecycle

```mermaid
erDiagram
    repositories ||--o{ index_jobs : requests
    repositories ||--o{ index_versions : owns
    repositories ||--o| index_versions : activates
    source_snapshots ||--o{ index_jobs : supplies
    source_snapshots ||--o{ index_versions : freezes
    index_versions o|--o{ index_versions : bases_on
    index_jobs o|--o| index_versions : builds
    index_jobs ||--o{ job_attempts : retries
    index_jobs o|--o| job_attempts : current_attempt
    index_versions ||--o{ index_artifacts : manifests
    index_versions ||--o{ validation_issues : validates
    index_versions ||--o{ capability_readiness : exposes
    validation_issues o|--o{ capability_readiness : explains
    index_artifacts o|--o{ job_attempts : checkpoints
    idempotency_records ||--o| index_jobs : deduplicates

    index_jobs {
      text id PK
      text repository_id FK
      text source_snapshot_id FK
      text target_index_version_id FK
      text current_attempt_id FK
      bigint lease_generation
    }
    job_attempts {
      text id PK
      text job_id FK
      text repository_id FK
      bigint lease_generation UK
      timestamptz lease_expires_at
    }
    index_versions {
      text id PK
      text repository_id FK
      bigint version_number UK
      text source_snapshot_id FK
      text base_index_version_id FK
      text lifecycle
    }
    index_artifacts {
      text id PK
      text repository_id FK
      text index_version_id FK
      char sha256
    }
    validation_issues {
      text id PK
      text repository_id FK
      text index_version_id FK
      text severity
    }
    capability_readiness {
      text id PK
      text repository_id FK
      text index_version_id FK
      text capability UK
      text state
    }
```

The repository-active-version and job-current-attempt relationships are intentional cycles. DAT-002 creates the base tables first and adds those FKs as deferred constraints. The active lifecycle is additionally checked by a deferred constraint trigger.

## Versioned code intelligence and graph

```mermaid
erDiagram
    index_versions ||--o{ files : contains
    index_versions ||--o{ symbols : contains
    index_versions ||--o{ endpoints : contains
    index_versions ||--o{ references : contains
    index_versions ||--o{ chunks : contains
    index_versions ||--o{ graph_candidates : evaluates
    index_versions ||--o{ graph_nodes : contains
    index_versions ||--o{ graph_edges : contains

    files ||--o{ symbols : defines
    files ||--o{ endpoints : declares
    files ||--o{ references : originates
    files ||--o{ chunks : locates
    files o|--o{ graph_candidates : supports
    files o|--o{ graph_nodes : locates
    files o|--o{ graph_edges : supports
    symbols o|--o{ endpoints : handles
    symbols o|--o{ references : originates
    index_artifacts o|--o{ chunks : stores_payload
    graph_nodes ||--o{ graph_edges : source
    graph_nodes ||--o{ graph_edges : target

    files {
      text id PK
      text repository_id FK
      text index_version_id FK
      text canonical_key UK
      text relative_path UK
    }
    symbols {
      text id PK
      text repository_id FK
      text index_version_id FK
      text canonical_key UK
      text file_id FK
    }
    endpoints {
      text id PK
      text repository_id FK
      text index_version_id FK
      text canonical_key UK
      text file_id FK
      text handler_symbol_id FK
    }
    references {
      text id PK
      text repository_id FK
      text index_version_id FK
      text canonical_key UK
      text source_file_id FK
      text source_symbol_id FK
    }
    chunks {
      text id PK
      text repository_id FK
      text index_version_id FK
      text canonical_key UK
      text file_id FK
      text artifact_id FK
    }
    graph_candidates {
      text id PK
      text repository_id FK
      text index_version_id FK
      text canonical_key UK
    }
    graph_nodes {
      text id PK
      text repository_id FK
      text index_version_id FK
      text canonical_key UK
      text file_id FK
    }
    graph_edges {
      text id PK
      text repository_id FK
      text index_version_id FK
      text canonical_key UK
      text source_node_id FK
      text target_node_id FK
    }
```

Every line in this diagram is repository/version scoped. In particular, graph edge source and target FKs are `(repository_id, index_version_id, node_id)`, so an edge cannot join nodes from different builds. Reverse relations are derived through `ix_graph_edges_reverse`; inverse edges are not duplicated.

## Evidence, conversations, claims, and traces

```mermaid
erDiagram
    operator_principals ||--o{ conversations : owns
    repositories ||--o{ conversations : scopes
    conversations ||--o{ messages : contains
    index_versions o|--o{ messages : grounds
    messages ||--o{ claims : asserts
    claims ||--o{ citations : supports
    evidence ||--o{ citations : cited_by
    index_versions ||--o{ evidence : validates
    files o|--o{ evidence : locates

    operator_principals ||--o{ agent_traces : initiates
    repositories ||--o{ agent_traces : scopes
    index_versions o|--o{ agent_traces : grounds
    conversations o|--o{ agent_traces : groups
    messages o|--o{ agent_traces : request_message
    messages o|--o{ agent_traces : response_message
    agent_traces ||--o{ agent_trace_events : records

    evidence {
      text id PK
      text repository_id FK
      text index_version_id FK
      text file_id FK
      text source_canonical_key
    }
    conversations {
      text id PK
      text principal_id FK
      text repository_id FK
    }
    messages {
      text id PK
      text conversation_id FK
      text repository_id FK
      text index_version_id FK
    }
    claims {
      text id PK
      text message_id FK
      text repository_id FK
      text index_version_id FK
    }
    citations {
      text id PK
      text claim_id FK
      text evidence_id FK
      text repository_id FK
      text index_version_id FK
    }
    agent_traces {
      text id PK
      text principal_id FK
      text repository_id FK
      text index_version_id FK
      text conversation_id FK
    }
    agent_trace_events {
      text id PK
      text trace_id FK
      int sequence UK
    }
```

Claims and citations are distinct: a claim belongs to one assistant message, while a citation joins that claim to validated evidence in the same repository/index version. Trace events store typed, privacy-safe events; they never store hidden chain-of-thought.

## Evaluation

```mermaid
erDiagram
    evaluation_datasets ||--o{ evaluation_cases : defines
    evaluation_datasets ||--o{ evaluation_runs : executes
    evaluation_runs ||--o{ evaluation_results : produces
    evaluation_cases ||--o{ evaluation_results : measures
    repositories o|--o{ evaluation_runs : scopes
    index_versions o|--o{ evaluation_runs : binds
    agent_traces o|--o{ evaluation_results : explains

    evaluation_datasets {
      text id PK
      text name
      text version
      char artifact_sha256
    }
    evaluation_cases {
      text id PK
      text dataset_id FK
      text case_key UK
    }
    evaluation_runs {
      text id PK
      text dataset_id FK
      text repository_id FK
      text index_version_id FK
      char configuration_sha256
    }
    evaluation_results {
      text id PK
      text run_id FK
      text case_id FK
      text trace_id FK
    }
```

Frozen datasets/cases and index versions used by evaluation evidence use `RESTRICT`. Repository deletion may null a non-release evaluation repository link only under retention policy; retained index-version evidence blocks cleanup until policy permits it.

## Cross-aggregate foreign-key catalog

| Child columns | Parent columns | Delete action | Purpose |
| --- | --- | --- | --- |
| `repositories.owner_principal_id` | `operator_principals.id` | `RESTRICT` | authorization boundary |
| `source_snapshots(repository_id, repository_source_id)` | `repository_sources(repository_id, id)` | `CASCADE` | immutable source ownership |
| `index_jobs(repository_id, source_snapshot_id)` | `source_snapshots(repository_id, id)` | `RESTRICT` | exact build input |
| `index_versions(repository_id, source_snapshot_id)` | `source_snapshots(repository_id, id)` | `RESTRICT` | version/source binding |
| `repositories(id, active_index_version_id)` | `index_versions(repository_id, id)` | `RESTRICT`, deferred | atomic active pointer |
| `index_jobs(repository_id, target_index_version_id)` | `index_versions(repository_id, id)` | `RESTRICT` | job output identity |
| `index_jobs(repository_id, current_attempt_id)` | `job_attempts(repository_id, id)` | `SET NULL`, deferred | current fencing attempt |
| all observation `(repository_id, index_version_id)` | `index_versions(repository_id, id)` | `CASCADE` except retained evidence | version ownership |
| graph edge node triples | graph node triples | `CASCADE` | same-version graph integrity |
| `citations(repository_id, index_version_id, evidence_id)` | evidence triple | `RESTRICT` | validated support binding |
| `claims(repository_id, index_version_id, message_id)` | message ownership tuple | `CASCADE` | claim/answer scope |
| `evaluation_runs(repository_id, index_version_id)` | version pair | `RESTRICT` | frozen evaluation identity |

The table dictionary is authoritative when this summary omits a nullable relation or a supporting unique key.
