# Production Readiness Plan

Status: Approved release-closure plan  
Authority: L3 workstream coordination; phase order is owned by `master-roadmap.md`  
Last verified: 2026-07-12

## Release target

Single-tenant self-hosted deployment supporting safe repository ingestion, durable indexing, deterministic exploration, evidence-backed Agentic RAG, impact analysis, evaluation, and operational recovery.

## Mandatory workstreams

- Data/migrations and durable job execution.
- Versioned artifacts, graph provenance/validation, atomic activation.
- Authentication boundary, import sandbox, secrets, rate/size limits.
- Scalable/versioned retrieval, evidence sufficiency, citations, trace/evaluation.
- Frontend navigation/server state/error/capability/graph behavior.
- CI/CD, telemetry, deployment, backup/restore, rollback, runbooks.

## Release decision

The release owner reviews `18-production-evidence/release-checklist.md`. Any open P0 gap, critical vulnerability/validation issue, missing recovery drill, or failed AI regression blocks release.

## Closure sequence

1. Freeze one release candidate, dependency lock, migrations, configuration, datasets, and deployment manifests.
2. Run the Phase 8 qualification suite without mixing evidence from different candidate revisions.
3. Create `18-production-evidence/releases/<version>/manifest.md` from the release manifest template.
4. Reconcile requirements, baseline, known limitations, runbooks, user/operations docs, and artifact checksums.
5. Review the L3 checklist and approve or reject explicitly.

This file does not repeat feature delivery phases or task dependencies.
