---
id: JOB-002
title: Select the production queue implementation by recovery and cancellation PoC
status: completed
priority: P0
phase: 2
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [JOB-001]
requirements: []
contracts:
  - docs/05-domain-contracts/indexing.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/adoption-process.md
  - docs/03-technology/stack-overview.md
  - docs/03-technology/technology-radar.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - poc/queue/**
  - docs/03-technology/stack-overview.md
  - docs/03-technology/technology-radar.md
  - docs/13-decisions/ADR-0003-production-job-queue.md
  - docs/16-agent-tasks/indexing/JOB-002-select-queue-by-poc-adr.md
  - docs/18-production-evidence/queue-selection-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/**
  - frontend/**
  - tests/**
  - storage/**
dependency_changes:
  allowed: true
  add:
    - rq==2.10.0 (PoC environment only)
    - dramatiq[redis]==2.2.0 (PoC environment only)
  remove: []
production_gates:
  - Queue payloads contain a JSON-safe job ID only; PostgreSQL remains authoritative.
  - A replacement worker observes redelivery after forced worker loss without manual broker mutation.
  - Queued cancellation prevents execution and running cancellation stops cooperatively at a checkpoint.
  - Broker outage fails submission observably and recovery does not create a second logical job.
evidence_outputs:
  - docs/18-production-evidence/queue-selection-report.md
---

# Task JOB-002 — Select the production queue implementation by recovery and cancellation PoC

## Objective

Compare the approved RQ and Dramatiq candidates with one reproducible Redis-backed harness, accept one queue implementation in an ADR, and leave production integration to `JOB-003`.

## In scope

- An isolated, pinned PoC environment that does not modify backend dependencies.
- Equivalent JSON job-ID delivery, forced-worker-loss recovery, queued cancellation, cooperative running cancellation, and broker-outage scenarios.
- Recorded timings, pass/fail results, operational/security/licensing assessment, accepted ADR, and technology-radar update.

## Out of scope

Application queue ports/adapters, worker deployment, PostgreSQL lease implementation, retries in application code, API changes, production configuration, and backend dependency installation.

## Existing code to reuse

- `JobStateStore` remains the future authoritative PostgreSQL command boundary.
- JOB-001 transition tests define the state ownership that queue delivery must not replace.

## Implementation sequence

1. Build an isolated Redis-backed harness with identical scenario inputs for both candidates.
2. Run each scenario three times and retain machine-readable results.
3. Reject a candidate on any correctness failure; compare operational complexity only among passing candidates.
4. Record the decision and defer production dependency/adapter changes to `JOB-003`.

## Data/API compatibility and migration

No application data, API, schema, or backend dependency changes are allowed. The PoC uses disposable Redis data and opaque job IDs.

## Failure, security, performance, and observability requirements

- Use JSON serialization and a trusted disposable Redis instance; never deserialize arbitrary pickle payloads.
- Each scenario has a 30-second hard timeout and records candidate, run, outcome, and elapsed milliseconds.
- Forced worker loss must be detectable and the same logical job ID must be processed by a replacement worker within the timeout.
- Cancellation is durable application intent simulated outside broker state; broker-native stop commands are not accepted as the source of truth.

## Required tests and commands

```powershell
docker compose -f poc/queue/compose.yml build
docker compose -f poc/queue/compose.yml run --rm benchmark
backend\.venv\Scripts\python.exe -m json.tool poc/queue/results.json
git diff --check
docker compose -f poc/queue/compose.yml down -v
```

The benchmark command must exit zero only when both candidate result sets are complete. The selected candidate must pass all correctness scenarios in all three runs. Results and interpretation are copied to `docs/18-production-evidence/queue-selection-report.md`.

## Acceptance criteria

- Both pinned candidates run the same five scenarios three times with no missing result.
- The selected candidate passes JSON payload, worker-loss recovery, queued cancellation, cooperative running cancellation, and broker-outage behavior in all runs.
- The ADR documents alternatives, versions, license/security, operations, failure behavior, migration, observability, and rollback.
- No backend manifest, lock, application source, test, or schema file changes.

## Rollback

Remove the isolated PoC and revert the ADR/technology-document updates. No runtime or data rollback is required.

## Documentation and evidence updates

Complete this task, add `ADR-0003`, update the stack/radar and project status, and publish the measured queue-selection report.
