# Deployment, Scaling, and Capacity Design

## Initial production topology

One self-hosted node may run reverse proxy, static web, API, workers, Redis, and PostgreSQL, but they remain separate processes/containers with independent health and resource limits. Database and artifacts use persistent backed-up storage.

## Scaling dimensions

- API replicas scale with concurrent HTTP/read workload and remain stateless except database/storage access.
- Index workers scale with CPU/memory and queue depth; concurrency is capped per host and per repository.
- Retrieval read replicas/caches are introduced only after measured database pressure.
- Artifact storage scales independently of database rows.
- LLM/embedding concurrency is governed by provider quotas and cost budgets.

## Supported repository classes

Before release, capacity tests establish Small/Medium/Large reference classes using file count, source bytes, indexable bytes, symbols, edges, chunks, and language mix. Each class records index duration, peak memory, artifact size, query p50/p95, and frontend projection performance.

Requests exceeding configured limits fail before expensive processing with safe diagnostics. Large repositories may use scoped indexing/projections, but the UI must disclose coverage.

## Failure boundaries

- API failure does not corrupt running jobs.
- Worker failure leaves an inactive build recoverable or safely failed.
- Broker outage prevents new delivery but authoritative job state remains.
- Artifact outage blocks build/publish and readiness, not metadata integrity.
- Optional provider outage yields deterministic or capability-limited results.
- Database outage makes the API unready; clients receive safe retryable errors.

## Deployment sequence

1. Validate configuration and secret references.
2. Verify database, broker, and artifact connectivity.
3. Acquire one migration lock and run supported migrations.
4. Start API and workers with readiness disabled until schema checks pass.
5. Start web/reverse proxy and enable traffic.
6. Run release smoke checks.

Rollback never points the active index to an unvalidated version. Database rollback is used only when explicitly supported; otherwise follow forward recovery with compatible application rollback.
