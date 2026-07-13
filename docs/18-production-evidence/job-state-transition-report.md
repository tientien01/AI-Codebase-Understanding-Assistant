# JOB-001 Job State Transition Report

Status: Locally verified; PR CI delegated to project owner

Verified: 2026-07-13

## Result

- Transactional submission creates the idempotency record, building target version, and queued job together.
- Job and version updates require both a declared transition edge and the expected persisted state.
- The one-active-job constraint rejects a second queued job and rolls back its candidate version.
- Artifact registration validates SHA-256, non-negative size/count, repository/version ownership, and rejects overwrite.
- Queue delivery, attempts, leases, heartbeat, retry/recovery, manifest readiness, and activation remain in their owning later tasks.

## Verification

| Gate | Result |
| --- | --- |
| JOB-001 targeted suite | 4 passed |
| Complete PostgreSQL suites | 18 passed |
| Complete backend suite | 78 passed, 1 existing duplicate-ZIP warning |
| Migration/dependency diff | None |
