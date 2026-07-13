# Database Design Requirements

The implementation plan must produce an ERD and Alembic migrations for at least: repositories, repository_sources, import_sessions, index_jobs, index_versions, index_artifacts, files, symbols, endpoints, references, chunks, graph_nodes, graph_edges, validation_issues, capability_readiness, evidence, conversations, messages, agent_traces, evaluation datasets/runs/results.

Required constraints include:

- One active index version per repository.
- At most one claimed/running build per repository unless explicitly supported.
- Unique canonical entity key per repository/index/type.
- Graph edges reference valid nodes in the same repository/index.
- Evidence references a valid repository/index/source range.
- Job transitions and timestamps are consistent.
- Idempotency keys are unique within their operation scope.

Required query indexes must be derived from endpoint and worker access patterns, not guessed. Migration tests cover empty install, upgrade from the supported previous release, rollback/recovery policy, and schema drift.

`DAT-001` fixes the implementation-ready design in `postgresql-physical-schema.md` and `postgresql-erd.md`. `DAT-002` owns its Alembic translation and may not invent or weaken physical semantics outside a separately authorized contract amendment.
