# Production Evidence

Status: Accepted evidence policy  
Authority: Release proof and audit trail  
Owner: Release owner  
Last verified: 2026-07-12

Evidence proves that requirements are implemented and operationally safe. Store generated reports or links to immutable CI artifacts by release: migrations, tests, benchmarks, security scans, performance/resilience, backup/restore, deployment smoke, and approvals.

## Release layout

Use `releases/<version>/manifest.md` as the index for migration, test, benchmark, security, performance, resilience, backup/restore, deployment, limitation, and approval evidence. Generated reports may remain in immutable CI/artifact storage; record version, checksum, command/configuration, result, and link here.

Evidence is append-only for an issued release. Corrections create a superseding report and preserve the original audit trail.

Traceability is: requirement → architecture/contract → ADR → task → test → report → release.
