# Reliability and Operations

`observability-and-slo-contract.md` owns correlation context, event/metric/span names, cardinality rules, SLIs, capacity-class measurement, threshold acceptance, alerts, and runbook linkage.

## Service objectives

SLOs and supported capacity are versioned after load testing. Availability excludes explicitly documented maintenance windows but not avoidable worker/provider failures.

## Observability

All requests/jobs propagate request, repository, job, and index-version correlation where applicable. Emit structured logs, metrics, and traces for API latency/errors, queue depth, job/stage duration, throughput, parser failures, validation issues, retrieval/citation quality, provider latency/tokens/cost, and storage usage.

## Health

- `/health/live`: process is alive.
- `/health/ready`: required schema, database, broker, and artifact store are usable.
- Optional LLM failure limits AI capability but does not make deterministic exploration unavailable.

## Operations

- Migrations run once before replicated API startup.
- Containers have resource limits, graceful shutdown, restart policy, and health checks.
- Backups cover database and required artifacts; restore drills verify consistency.
- Rollback preserves compatible data or follows documented forward-recovery policy.
- Runbooks under `17-runbooks/` cover stuck jobs, failed validation, unavailable dependencies, migration, restore, and security incidents.

`specifications/error-handling-and-fallback.md` defines the error envelope, error codes, UI mapping, parser/provider/vector/graph/citation fallbacks, stale and insufficient-evidence behavior, production failure policy, and readiness responses.
