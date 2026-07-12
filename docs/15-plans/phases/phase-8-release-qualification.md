# Phase 8 — L3 Release Qualification

Status: Approved; blocked by all mandatory L3 workstreams

## Outcome

One immutable release candidate satisfies every accepted requirement and L3 gate on the same versioned configuration, with limitations and recovery procedures documented.

## Tasks

`EXT-001` when required for production v1, then `REL-001` and `REL-002`.

## Entry

All P0/P1 implementation tasks are complete; migrations, artifacts, benchmark datasets, deployment manifests, and dependency locks are frozen for the candidate.

## Exit gates

- Unit, integration, contract, E2E, security, performance, resilience, incremental-equivalence and AI regression suites pass.
- Production deployment, migration, backup/restore, provider degradation and rollback/forward-recovery drills pass.
- No open critical vulnerability, P0 gap, invalid graph/evidence condition, placeholder mandatory UI, or undocumented critical dependency remains.
- Traceability links every release requirement to contract, task, test and immutable report.
- Release checklist is reviewed and signed by the release owner.

## Evidence

Complete `18-production-evidence/releases/<version>/` manifest and signed release checklist. Completion promotes `project-status.md` to L3 only after approval.
