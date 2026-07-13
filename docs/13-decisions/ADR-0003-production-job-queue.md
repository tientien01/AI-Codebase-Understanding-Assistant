# ADR-0003: Production Job Queue

Status: Accepted

Owner: Project maintainer

Last verified: 2026-07-13

Dependencies: `ADR-0001-production-foundations.md`, `../03-technology/adoption-process.md`, `../05-domain-contracts/indexing/detailed-indexing-pipeline.md`

## Context

Production indexing needs at-least-once Redis delivery to dedicated workers while PostgreSQL remains authoritative for job, attempt, lease, retry, cancellation, and activation state. The approved candidates were RQ and Dramatiq. JOB-002 measured JSON-safe ID delivery, forced worker loss, queued and running cancellation, and broker outage with the same isolated harness.

RQ 2.10.0 passed 12 of 15 runs but did not redeliver a forcibly interrupted job to a replacement worker within the 30-second gate in any run. Its documented abandoned-job path moves interrupted work to `FailedJobRegistry`, so timely recovery needs additional registry/scheduler policy. Dramatiq 2.2.0 passed all 15 runs; its Redis broker redelivered the unacknowledged message in 3.181–3.894 seconds under the PoC heartbeat settings.

## Decision

- Adopt **Dramatiq 2.2.0 with its Redis broker** as the production queue implementation for the first single-node release.
- Queue messages contain one JSON-safe opaque `job_id`; workers reload all authority and input from PostgreSQL.
- Delivery is at least once. A duplicate or stale delivery must fail the PostgreSQL lease/fencing predicate rather than execute a second logical job.
- Durable cancellation remains a PostgreSQL flag observed before work and at cooperative stage checkpoints. Dramatiq time limits and shutdown notifications are safety aids, not cancellation authority.
- Disable Dramatiq's actor-level automatic exception retries for indexing delivery. JOB-004 owns the persistent attempt budget, error classification, backoff, and recovery policy.
- Broker publication failure is observable. JOB-003 must preserve the queued database record and provide an idempotent redispatch path; it must not claim a cross-system transaction.
- The production heartbeat/offline threshold is configuration with telemetry and resilience evidence. The PoC's two-second threshold is test acceleration, not a production default.
- JOB-003 owns the locked backend dependency, queue port/adapter, worker entrypoint, configuration, and deployment changes. This ADR does not install a production dependency.

## Alternatives considered

### RQ 2.10.0

RQ has a smaller conceptual surface, BSD-2-Clause licensing, an explicit JSON serializer, process-isolated workers, Windows-compatible `SpawnWorker`, and native commands for stopping an executing job. It was rejected for this release because forced worker loss did not satisfy the automatic recovery gate without adding failed-registry/scheduler coordination. Native stop commands also cannot replace durable cancellation intent.

### Dramatiq 2.2.0

Dramatiq uses JSON messages by default, supports Redis, worker processes and threads, broker heartbeats, unacknowledged-message recovery, middleware, and Prometheus-compatible metrics. Its LGPL-3.0-or-later license is acceptable for use as an unmodified dynamically imported library; redistribution must preserve applicable notices and replacement rights. Operationally, indexing workers will use one thread per process initially because parsing is CPU-heavy and application concurrency must remain bounded.

### Custom Redis queue

A custom Redis list/stream implementation was rejected because it would recreate acknowledgement, redelivery, shutdown, middleware, and observability behavior without a measured requirement that justifies that ownership.

## Security, failure, and observability

- Redis is trusted infrastructure and is not exposed as an untrusted message-ingestion surface.
- Do not enable pickle or another executable serializer. Reject messages whose actor, queue, argument count, or job-ID form is unexpected.
- Broker outage, enqueue error, worker loss, redelivery, duplicate delivery, cancellation latency, queue depth/age, and dead letters must be structured and measurable.
- A worker must stop writes after lease loss even when queue execution continues.
- Default Dramatiq retries are not accepted application policy; persistent PostgreSQL transitions remain the audit trail.

## Migration, enforcement, and rollback

JOB-003 replaces production process-local dispatch behind a queue port while keeping the local deterministic adapter. JOB-004 adds leases and recovery before production activation. Rollback stops Dramatiq workers, restores the prior adapter, and retains queued PostgreSQL jobs for later redispatch; Redis messages contain no authoritative state to migrate.

Enforcement is provided by the locked dependency, JSON/job-ID conformance tests, duplicate-delivery and restart tests, configuration validation, and the JOB-004 resilience suite.

## Evidence and official references

- Measured report: `../18-production-evidence/queue-selection-report.md`
- [Dramatiq retries, limits, and dead letters](https://dramatiq.io/guide.html)
- [Dramatiq Redis broker and heartbeat recovery](https://dramatiq.io/_modules/dramatiq/brokers/redis.html)
- [Dramatiq middleware and Prometheus support](https://dramatiq.io/reference.html)
- [RQ worker lifecycle and stop commands](https://python-rq.org/docs/workers/)
- [RQ interruption behavior](https://python-rq.org/docs/results/)
