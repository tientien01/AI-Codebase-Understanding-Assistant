# Phase 7 — Security and Operations

Status: Approved; SEC-001 import-acquisition hardening is complete

## Outcome

The L3 deployment safely handles untrusted repositories, enforces the accepted access boundary, exposes actionable telemetry, and can be deployed, backed up, restored, rolled forward/back, and operated from runbooks.

## Tasks

`SEC-001`, `SEC-002`, and `OPS-001` through `OPS-003`.

## Entry

Production persistence/job topology is known; threat model, capacity classes, secret boundaries, and deployment profile are accepted.

## Exit gates

- Archive/Git acquisition, parsers, providers, exports, logs and deletion satisfy the threat model and quotas.
- Authentication, repository authorization, audit and credential-reference design pass boundary tests.
- Structured logs, metrics, traces, liveness/readiness and correlation cover critical flows.
- Locked non-root containers and Compose/TLS profile pass deployment smoke tests.
- Backup/restore consistency, worker recovery, migration, rollback/forward-recovery and incident runbooks are drilled.

## Evidence

Adversarial security suite, authorization report, SBOM/vulnerability scan, telemetry/readiness tests, deployment smoke, restore and recovery drills.

`SEC-001` now has a network-free adversarial implementation for archive/folder/public-Git path, quota, subprocess-hardening and cleanup controls. Its 49-test focused gate and mandatory full backend suite with 294 passed and 29 integration-profile skips are clean. SEC-001 is complete; no Phase 7 exit claim is made because the remaining security and operations tasks and evidence are still open.
