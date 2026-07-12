# Release Levels

Status: Accepted  
Authority: Release maturity classification  
Owner: Release owner  
Dependencies: `definition-of-production-ready.md`  
Last verified: 2026-07-12

Release levels make progress visible without weakening the final production definition. A level is achieved only when its evidence set is complete.

| Level | Intended use | Required outcome |
| --- | --- | --- |
| L0 — Development | Maintainer workstation | Reproducible setup, deterministic targeted tests, known baseline, no claim of user readiness |
| L1 — Demo | Controlled local demonstration | Complete happy path on supported fixtures, no fake mandatory UI, safe failure messages, documented limitations |
| L2 — Portfolio | Repeatable technical evaluation | CI, architecture traceability, benchmark report, representative E2E flows, reproducible build and demo |
| L3 — Self-hosted production | Single-tenant deployment on one managed node | Durable jobs, PostgreSQL migrations, atomic indexes, access control, telemetry, backups, recovery, security and load evidence |
| L4 — Public production | Internet-facing or multi-user service | Tenant isolation or explicit user boundary, stronger abuse controls, HA/SLO evidence, incident process, compliance decisions |

## Target

Production v1 targets **L3**. L4 is explicitly deferred and requires new product requirements, threat modeling, capacity goals, ADRs, and tasks.

## Promotion rule

- Every lower level must remain satisfied.
- Required reports are stored under `18-production-evidence/releases/<release>/` or linked to immutable CI artifacts.
- Open P0 gaps, critical vulnerabilities, failed recovery, or failed grounding thresholds block promotion.
- A level may be revoked when a regression invalidates its evidence.

## Evidence summary

| Level | Minimum evidence |
| --- | --- |
| L0 | setup verification, targeted tests, baseline report |
| L1 | demo E2E, supported fixture manifest, limitation register |
| L2 | CI reports, production build, retrieval/citation benchmark, architecture traceability |
| L3 | migration, security, resilience, load, deployment, backup/restore and release approval |
| L4 | multi-user/tenant, abuse, HA, SLO and incident-response evidence defined by a future ADR |
