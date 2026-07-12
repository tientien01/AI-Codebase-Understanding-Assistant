# Definition of Production Ready

Status: Accepted  
Authority: L3 release gate  
Owner: Release owner  
Dependencies: `release-levels.md`, accepted contracts and ADRs  
Last verified: 2026-07-12

This document defines **L3 single-node self-hosted production**. Earlier maturity levels are defined in `release-levels.md`; they do not weaken these requirements.

A release is production-ready only when all mandatory gates pass:

- Approved scope and measurable non-functional requirements.
- Versioned database migrations tested from a supported previous release.
- Durable, idempotent jobs with retry, cancellation, heartbeat, recovery, and atomic index activation.
- Authentication, authorization model, input limits, import isolation, secret filtering, and threat-model mitigations.
- Structured logs, metrics, traces, liveness/readiness, alerts, and operator runbooks.
- Backup and restore drill; documented rollback and disaster recovery.
- Unit, integration, contract, E2E, security, performance, resilience, and incremental-equivalence tests.
- RAG benchmark thresholds for retrieval, citation accuracy, hallucination, insufficient evidence, latency, and cost.
- Dependency, license, vulnerability, and container checks.
- Production deployment smoke test and signed release checklist.

No placeholder UI, fake provider, process-local job control, manual schema patch, or undocumented critical dependency may be on the mandatory production path.
