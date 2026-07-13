# Runbook — Stuck or stale index job

Status: Implemented; production exercise pending deployment task

Owner: Indexing operator

Last exercised: 2026-07-13 (automated PostgreSQL/Redis integration profile)

Related alerts/dashboards: lease-expiration, queue-backlog, and repeated-job-failure telemetry pending OPS-001

Related components/contracts: `JobStateStore`, `JobDeliveryService`, indexing contract, JOB-004 resilience report

## Trigger and impact

- Detection signal: a job remains `running` past its attempt lease, repeated deliveries report `recovery_scheduled`, or the attempt budget becomes exhausted.
- User-visible impact: the current indexing request is delayed or failed; the last active index remains the only usable version.
- Data/integrity risk: manually changing Redis or job rows can bypass generation fencing and allow conflicting workers.
- Capabilities affected: only the candidate index build and job status; an already active version must remain available.

## Preconditions and safety

- Required access: read access to PostgreSQL job/attempt state and supported worker restart/redispatch controls.
- Backup/snapshot requirement: preserve the incident job/attempt rows and timestamps before any approved recovery mutation.
- Commands/actions that must not be run: do not delete Redis keys, edit lease timestamps/generations, clear `current_attempt_id`, or mark a version active manually.
- Secret/redaction considerations: record opaque IDs, state, generation, stage, and UTC timestamps only; never copy database/Redis URLs, worker internals, source content, or credentials.

## Diagnosis

1. Record the repository ID, job ID, target version ID, state, stage, cancellation flag, current attempt ID, lease generation, and UTC observation time.
2. Read the current attempt state, `heartbeat_at`, `lease_expires_at`, and safe error code. Compare timestamps in UTC; do not infer authority from worker identity alone.
3. Confirm PostgreSQL is reachable and at Alembic head, Redis is reachable, and a dedicated indexing worker is running.
4. Classify the condition:
   - unexpired lease: wait for heartbeat or the declared expiry; duplicate delivery will schedule recovery;
   - expired lease: normal redelivery may claim the next generation;
   - cancellation requested: the current worker should stop at its next safe boundary;
   - queued after publication failure: use the supported idempotent redispatch path;
   - terminal/exhausted: do not redispatch the same job.

## Containment

Stop only the affected worker when it is demonstrably unhealthy. Keep PostgreSQL and Redis intact so the current lease can expire and the authoritative attempt history remains available. Do not start an unfenced manual pipeline.

## Recovery

1. Restore PostgreSQL/Redis connectivity before restarting the dedicated worker. Expected result: readiness succeeds without changing the job row.
2. Start exactly the configured worker concurrency. Expected result: an unacknowledged or idempotently redispatched job ID reaches `JobDeliveryService`.
3. For an unexpired attempt, allow the scheduled delivery to wait until lease expiry. Expected result: no second runner invocation before expiry.
4. After expiry, verify the old attempt becomes `lease_lost`, `lease_generation` increments once, and a new current attempt enters `running`.
5. If the job is queued because Redis publication failed, invoke only the application-supported redispatch operation. If that operation is unavailable, preserve the row and escalate to the indexing owner; do not enqueue an ad hoc payload.
6. If the attempt budget is exhausted or the error is permanent, leave the job terminal and submit a new idempotent indexing request only after correcting the cause.

## Verification

- Health/readiness checks: PostgreSQL, Redis, and one dedicated worker are ready; queue backlog age decreases.
- Data/index consistency checks: one current attempt matches the job generation; older attempts are terminal; no failed/cancelled candidate is active.
- User-flow smoke test: job polling reaches one terminal outcome and the previous active index remains usable on failure/cancellation.
- Telemetry recovery: no continuing lease-expiration/repeated-failure signal for the recovered job; record the missing telemetry limitation until OPS-001.

## Cleanup and follow-up

- Temporary artifacts/leases: cleanup is deferred to the owning immutable-artifact/retention tasks; never delete by guessed path.
- Incident/evidence location: link the incident record to `docs/18-production-evidence/job-resilience-report.md` or the release-specific evidence manifest.
- Corrective task/ADR: amend the owning indexing/operations task when recovery required behavior outside this runbook.
- Required regression test: reproduce worker loss, stale generation, cancellation, or retry classification in `tests/jobs/test_job_resilience.py`.
