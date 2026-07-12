---
id: DOC-003
title: Complete concrete cross-cutting production contracts
status: completed
priority: P0
phase: 0
owner: project-maintainer
last_verified: 2026-07-12
depends_on: [DOC-002]
requirements: []
contracts:
  - docs/04-domain-and-data/README.md
  - docs/05-domain-contracts/README.md
  - docs/07-security/README.md
  - docs/08-reliability-and-operations/README.md
  - docs/09-frontend-and-ux/README.md
  - docs/10-ai-rag-and-evaluation/README.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/stack-overview.md
allowed_paths:
  - docs/**
forbidden_paths:
  - backend/**
  - frontend/**
  - tests/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Identity/artifact, retrieval/trace/evaluation, threat, telemetry/SLO, and UX interaction contracts are implementable without inventing missing semantics.
evidence_outputs:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/10-ai-rag-and-evaluation/runtime-and-dataset-contracts.md
  - docs/07-security/threat-model.md
  - docs/08-reliability-and-operations/observability-and-slo-contract.md
  - docs/09-frontend-and-ux/interaction-contracts.md
---

# Task DOC-003 — Complete Concrete Cross-Cutting Production Contracts

## Context

Detailed specifications describe the intended system broadly, but implementation tasks still need exact cross-domain formats and ownership for stable identity, artifacts, ranking/traces/datasets, threats, telemetry/SLOs, and shared UX state.

## Objective

Add compact normative contracts that resolve those cross-cutting ambiguities while linking rather than repeating existing detailed specifications.

## In scope

- Define versioned canonical identities, provenance, artifact manifest and activation rules.
- Define normalized retrieval candidates, deterministic ranking ties, evidence selection, agent trace and evaluation dataset records.
- Add a threat/control/evidence register, telemetry naming/cardinality rules, SLI/SLO acceptance process, and frontend route/entity/state contracts.
- Reconcile owning README files and navigation.

## Out of scope

- Selecting unapproved infrastructure or numeric release thresholds without benchmark evidence.
- Implementing schemas, APIs, telemetry, UI, security controls or evaluation code.
- Repeating endpoint/entity/page details already owned by detailed specifications.

## Existing code to reuse

Use accepted domain summaries, detailed specifications, ADR-0001, Phase 0 baseline, and task register identifiers.

## Implementation sequence

1. Identify cross-cutting ambiguities not fully owned by current detailed specifications.
2. Add one compact canonical contract per owning domain.
3. Link ownership from README and delivery phases.
4. Validate internal references, UTF-8, headings, fences, stale paths and whitespace.

## Data/API compatibility and migration

These are target contracts. Current implementation remains baseline/partial until authorized tasks migrate it; no data/API change occurs in this task.

## Failure, security, performance, and observability requirements

Do not encode secrets, vendor-specific assumptions, unmeasured capacity claims, or hidden chain-of-thought. Every production control maps to a future task and evidence type.

## Required tests and commands

Run the complete documentation structural/reference validation and `git diff --check -- docs`.

## Acceptance criteria

- A future task can implement each contract without choosing undocumented IDs, state transitions, telemetry names, dataset fields, URL state, or threat handling.
- Existing detailed specifications retain field/page depth; new contracts own only cross-cutting invariants and exact interchange formats.
- All new documents identify authority, owner, dependencies and verification date.

## Rollback

Revert documentation-only changes; runtime behavior and data are unaffected.

## Documentation and evidence updates

Update owning README files, Phase 0 status, task register and project status.

## Completion evidence

Verified on 2026-07-12: all non-archive Markdown passed UTF-8, one-H1, balanced-fence, internal backticked-reference and Markdown-link validation; no stale promoted-document reference remains outside archive; tracked docs diff whitespace validation passed.
