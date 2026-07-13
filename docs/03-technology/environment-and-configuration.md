# Environment and Configuration Contract

Status: Accepted production v1 contract  
Authority: Runtime configuration names, profile defaults, and settings safety  
Owner: Platform and security owners  
Dependencies: `stack-overview.md`, `stack-profiles.md`, `../13-decisions/ADR-0001-production-foundations.md`  
Related source: `../../backend/app/core/config.py`  
Related tests: startup configuration, settings redaction, production-profile smoke tests  
Last verified: 2026-07-12

## Ownership and precedence

Only the backend configuration module reads process environment variables. Precedence is explicit command-line/deployment override, process environment, profile defaults, then code defaults. Production rejects unknown critical settings and fails startup when required values are absent or incompatible.

Runtime secrets come from the deployment secret mechanism and are represented in domain records by opaque references. APIs, logs, traces, manifests, and frontend state never return raw secret values. Imported repository `.env` files are untrusted source and are never runtime configuration.

## Profiles

| Concern | Test | Local | Production |
| --- | --- | --- | --- |
| Database | temporary SQLite | SQLite | PostgreSQL |
| Jobs | deterministic fake/in-process test adapter | optional Redis worker | Redis-backed durable worker selected by accepted ADR |
| Artifacts | temporary filesystem | filesystem | backed-up filesystem is valid for single-node L3; S3-compatible storage is optional |
| Retrieval | deterministic fake/index | deterministic exact/lexical | deterministic exact/lexical/metadata/graph; semantic optional |
| Providers | fake | fake or explicitly configured | optional, timeout/cost/redaction controlled |
| Auth | test principal | development compatibility | accepted single-operator identity/access model; blank/shared development token forbidden |

`APP_ENV` accepts `test`, `local`, or `production` and defaults to `local`. The production value requires a PostgreSQL `DATABASE_URL`; SQLite or a database that is unavailable or not at the repository Alembic head fails application composition before requests are served. Database URLs are never included in the stable startup error.

## Canonical configuration groups

Names below are the public configuration contract. A task that changes a name must provide compatibility, migration, and rollback.

```text
APP_ENV
API_V1_PREFIX
PUBLIC_ORIGIN
DATABASE_URL
REDIS_URL
ARTIFACT_ROOT
REPOSITORY_STORAGE_ROOT
IMPORT_STAGING_ROOT
AUTH_MODE
AUTH_SECRET_REF

MAX_UPLOAD_BYTES
MAX_ARCHIVE_ENTRIES
MAX_ARCHIVE_EXPANDED_BYTES
MAX_ARCHIVE_RATIO
MAX_REPOSITORY_FILES
MAX_REPOSITORY_BYTES
MAX_INDEXABLE_BYTES
MAX_FILE_BYTES
IMPORT_SESSION_TTL_SECONDS

INDEX_WORKER_CONCURRENCY
INDEX_PER_REPOSITORY_CONCURRENCY
INDEX_STAGE_TIMEOUT_SECONDS
INDEX_LEASE_SECONDS
INDEX_HEARTBEAT_SECONDS
INDEX_MAX_ATTEMPTS
INDEX_ARTIFACT_RETENTION_DAYS
INDEX_DEBUG_RETENTION_DAYS

GRAPH_MAX_DEPTH
GRAPH_MAX_NODES
GRAPH_MAX_EDGES
FILE_RANGE_MAX_BYTES
QUERY_PAGE_MAX_SIZE

RANKING_CONFIG_ID
MAX_RETRIEVAL_CANDIDATES
MAX_EVIDENCE_ITEMS
MAX_CONTEXT_TOKENS
AGENT_MAX_ROUNDS
AGENT_MAX_TOOL_CALLS
AGENT_MAX_SECONDS
AGENT_MAX_INPUT_TOKENS
AGENT_MAX_OUTPUT_TOKENS
AGENT_MAX_PROVIDER_COST

LLM_PROVIDER
LLM_MODEL
LLM_CREDENTIAL_REF
LLM_TIMEOUT_SECONDS
EMBEDDING_PROVIDER
EMBEDDING_MODEL
EMBEDDING_CREDENTIAL_REF
EMBEDDING_BATCH_SIZE

OTEL_EXPORTER_ENDPOINT
METRICS_ENABLED
LOG_LEVEL
```

Numeric values are deployment inputs, not universal defaults. `REL-001` capacity evidence must establish accepted Small/Medium/Large values on the reference environment. Until then production startup requires explicit limits and release evidence records them; the UI must not invent capacity labels.

## Immutable build configuration

Every index manifest records immutable component identifiers derived from code/package versions and accepted configuration:

- pipeline, scan schema, parser bundle, resolver rules, framework rules;
- graph schema and normalizer;
- chunker and ranking configuration;
- embedding model/dimension when semantic search is enabled;
- enrichment prompt/workflow versions when optional AI artifacts are enabled.

Operators do not manually declare parser/schema versions through ad hoc environment values. A version change creates a new compatible build or fails preflight; it never mutates an active artifact.

Atomic activation, authorization, source validation, secret filtering, evidence validation, and required quotas are invariants, not feature flags. Optional semantic search, architecture enrichment, guided tours, and provider-backed answer generation may be disabled and must degrade through capability readiness.

## Settings API boundary

The settings API may expose effective non-secret values, supported provider/model identifiers, whether a credential reference is configured, and which values require restart or re-index. It may mutate only an allowlisted set of non-security preferences.

It must not expose or disable credentials, authorization, archive/source validation, secret controls, atomic activation, evidence validation, mandatory resource limits, or release telemetry. Provider changes validate compatibility and report whether re-embedding or a new index version is required.

## Verification

Required evidence includes profile-specific startup tests, unknown/missing/incompatible-setting failures, redaction tests, settings allowlist tests, production smoke with PostgreSQL/Redis/artifacts/auth, and a manifest test proving effective build configuration is captured without secrets.
