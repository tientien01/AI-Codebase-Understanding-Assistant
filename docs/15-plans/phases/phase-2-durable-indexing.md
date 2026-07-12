# Phase 2 — Durable and Atomic Indexing

Status: Approved; blocked by Phase 1 persistence

## Outcome

Indexing survives process and delivery failures, produces immutable validated artifacts, and activates a version atomically without risking the last valid index.

## Tasks

`JOB-001` through `JOB-004` and `IDX-001` through `IDX-003`.

## Entry

Production repositories and transaction boundaries exist; queue candidates have a recovery/cancellation PoC plan.

## Exit gates

- Jobs, attempts, leases, heartbeats, cancellation, retry, and recovery are persistent and idempotent.
- Dedicated workers perform CPU-heavy indexing; API processes only submit/observe.
- Artifact manifests are immutable, checksum-addressed, and storage-port backed.
- Validation blocks invalid builds; activation is one transactional state change.
- Worker crash, broker outage, duplicate delivery, cancellation, corruption, and failed-build preservation tests pass.

## Evidence

Queue selection ADR, job transition suite, resilience report, manifest/checksum tests, and atomic activation report.
