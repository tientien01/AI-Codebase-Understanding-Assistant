# System Failure Model

Status: Accepted control model  
Authority: Cross-component failure ownership  
Owner: Reliability owner  
Dependencies: Security, indexing and error-handling contracts  
Last verified: 2026-07-12

Detailed error envelopes and codes remain in `08-reliability-and-operations/specifications/error-handling-and-fallback.md`. This document owns failure boundaries and recovery expectations.

| Failure | Authoritative state | Required containment and recovery | Required evidence |
| --- | --- | --- | --- |
| Upload interrupted/expired | Import session in database | Expire isolated temporary source; confirmation remains idempotent | import integration test |
| Unsafe archive/Git source | Rejected import diagnostic | Stop before publication; redact unsafe details; clean temporary data | adversarial import suite |
| Parser file failure | Build diagnostic artifact | Continue only when contract permits partial capability; never fabricate facts | parser fault fixtures |
| Worker crash/timeout | Job lease and inactive version | Lease expires; recover/retry within policy; active version unchanged | worker-kill test |
| Duplicate queue delivery | Job/version state and idempotency key | One valid transition/build effect; later delivery no-ops or resumes safely | redelivery test |
| Cancellation | Persistent job state | Stop at safe boundary, mark terminal state, retain/clean artifacts by policy | cancel E2E |
| Redis outage | Database job state | Reject/defer new delivery safely; reconcile after broker recovery | broker outage drill |
| Artifact write/corruption | Manifest/checksum plus version state | Block validation/publish; quarantine or rebuild; active version unchanged | checksum fault test |
| Database outage | Database | API/worker become unready; do not continue authoritative transitions | readiness test |
| Migration failure | Migration ledger/database backup | Keep traffic disabled; restore or forward-recover by runbook | migration drill |
| LLM/embedding failure | Provider call record/trace | Fall back to deterministic capability or return limited safe result | provider fault test |
| Insufficient evidence | Evidence selection result | Refuse or qualify; do not generate unsupported technical claims | negative benchmark |
| Stale citation | Evidence/index versions | Preserve old evidence for audit, mark stale, offer current version | stale evidence test |
| Oversized graph/query | Projection budget and diagnostics | Return bounded/truncated result with explicit coverage | large graph test |
| Backup/restore inconsistency | Database and artifact manifests | Keep service unready until active-version consistency validates | restore drill |

## Universal rules

- Errors carry request, repository, job, and index correlation where applicable without secrets.
- Retryability is explicit; clients do not guess from status text.
- Cleanup is idempotent and never follows untrusted paths.
- Partial results are returned only when the owning capability defines a safe `limited` state.
- Every production-critical failure row must eventually have a runbook and automated or drilled evidence.
