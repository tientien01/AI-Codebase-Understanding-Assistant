# Production Component Catalog

## Web application

**Responsibilities:** repository management, import preview, job observation, code/graph/API exploration, search, assistant, impact, evidence, evaluation, settings. It consumes versioned API contracts and never reconstructs domain truth from presentation state.

**Does not:** parse source, infer relations, validate evidence, hold authoritative job state, or embed provider credentials.

## FastAPI API

**Responsibilities:** authenticate and authorize, validate requests, apply quotas/idempotency, call application use cases, expose read models, submit durable jobs, return safe errors and correlation IDs.

**Does not:** execute CPU-heavy indexing, directly contain parser/retrieval/graph logic, or run migrations independently in each replica.

## Application use cases

Organized by ingestion, repositories, indexing, exploration, retrieval, assistant, impact, evaluation, and settings. They coordinate domain services and infrastructure ports within explicit transactions. They replace the current system-wide facade incrementally.

## Import subsystem

- `ImportSessionService`: session state machine and confirmation.
- `SourceAcquirer`: upload/Git acquisition with limits.
- `ImportPreviewBuilder`: safe scan statistics, warnings, language/framework summary.
- `DuplicateDetector`: stable fingerprint candidates.
- `SourcePublisher`: atomic move/copy into repository-owned storage.

Temporary sources are isolated and expire. Confirmation is idempotent; partial publication is rolled back safely.

## Durable job subsystem

- `IndexJobRepository`: authoritative PostgreSQL state.
- `QueuePort`: delivery of job IDs.
- `JobCoordinator`: submission, claim, lease, heartbeat, retry, cancellation, recovery.
- `IndexWorker`: executes one claimed build with resource limits.

Queue redelivery is expected. Correctness comes from idempotency, database constraints, leases, and versioned artifacts—not exactly-once delivery assumptions.

## Index pipeline

- Scanner creates a canonical inventory and fingerprints.
- Language adapters emit typed file-local facts/IR.
- Resolver binds imports/references/calls to canonical entities.
- Analysis extensions create CFG/DFG where supported.
- Candidate emitter preserves provenance.
- Graph assembler/normalizer enforces schema and records diagnostics.
- Chunk/search builders produce retrieval artifacts.
- Optional semantic enrichment emits labeled inferred artifacts.
- Validator calculates issues and capability readiness.
- Publisher atomically activates the validated version.

Each phase reads only declared artifacts and can be tested without FastAPI or an LLM.

## Query and understanding subsystem

- `RepositoryReadModel`: overview, files, symbols, endpoints, versions, readiness.
- `ProjectionService`: bounded graph projections and expansion.
- `Retriever` implementations: exact, lexical/BM25, metadata, semantic, graph.
- `CandidateMerger/Ranker`: normalized, versioned ranking.
- `EvidenceSelector`: converts eligible results into validated evidence.
- `ContextBuilder`: token-budgeted prompt context.
- `AgentOrchestrator`: bounded routing/tool use/repair.
- `CitationValidator`: validates final claim references.

## Evaluation subsystem

Runs versioned datasets against keyword, naive RAG, and production methods. It persists configuration, model/index versions, per-question evidence/answers/traces, aggregate metrics, and immutable exports.

## Infrastructure adapters

- PostgreSQL repositories.
- Redis-backed queue implementation.
- Local and S3-compatible artifact stores.
- Git provider with protocol/network limits.
- LLM and embedding providers with timeouts, redaction, cost/telemetry, and deterministic fakes.
- Telemetry exporters.

All adapters are replaceable through narrow ports; provider-specific types do not cross application boundaries.
