---
id: DAT-001
title: Define the production PostgreSQL schema and ERD
status: completed
priority: P0
phase: 1
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [FND-001]
requirements: []
contracts:
  - docs/04-domain-and-data/identity-and-artifact-contract.md
  - docs/04-domain-and-data/specifications/detailed-data-model.md
  - docs/04-domain-and-data/specifications/detailed-storage-design.md
  - docs/05-domain-contracts/indexing/detailed-indexing-pipeline.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/stack-profiles.md
baseline_docs:
  - docs/14-implementation-baseline/verification-report.md
allowed_paths:
  - docs/04-domain-and-data/README.md
  - docs/04-domain-and-data/database-design.md
  - docs/04-domain-and-data/postgresql-physical-schema.md
  - docs/04-domain-and-data/postgresql-erd.md
  - docs/16-agent-tasks/persistence/DAT-001-postgresql-schema-and-erd.md
  - docs/18-production-evidence/schema-design-review-report.md
  - docs/project-status.md
forbidden_paths:
  - backend/**
  - frontend/**
  - tests/**
  - storage/**
  - docs/04-domain-and-data/physical-schema-blueprint.md
  - docs/04-domain-and-data/specifications/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - The physical schema covers every accepted production aggregate and separates database IDs, canonical keys, versioned observations, and evidence IDs.
  - The ERD and foreign-key catalog enforce repository and index-version ownership without cross-version graph or evidence references.
  - Constraints and indexes are tied to accepted lifecycle invariants and named API/worker access patterns.
  - DAT-002 can translate the design into ordered Alembic revisions without inventing tables, keys, types, lifecycle values, or migration ordering.
evidence_outputs:
  - docs/18-production-evidence/schema-design-review-report.md
---

# Task DAT-001 — Define the Production PostgreSQL Schema and ERD

## Context

The current local profile persists nine SQLite tables through SQLAlchemy `create_all` and manual column patches. Production contracts require PostgreSQL authority for repository ownership, import confirmation, durable jobs and attempts, immutable index versions, canonical code observations, evidence, assistant traces, evaluation, audit, retention, and atomic activation. `DAT-002` cannot add a safe migration history until these physical boundaries are explicit.

## Objective

Publish an implementation-ready PostgreSQL table dictionary and ERD that fix table names, column types, nullability, keys, lifecycle checks, foreign keys, uniqueness, indexes, transaction boundaries, and migration order without changing runtime code or creating migrations.

## In scope

- Define PostgreSQL naming, opaque-ID, timestamp, JSON, checksum, canonical-key, and enum/check-value conventions.
- Specify access, repository/source/import, jobs/attempts, index/artifact/readiness, code intelligence, graph, evidence/assistant, evaluation, idempotency, deletion, and audit tables.
- Specify exact primary keys, repository/index ownership keys, composite foreign keys, uniqueness and lifecycle checks.
- Derive indexes from documented API, worker recovery, activation, cleanup, graph, evidence, conversation, and evaluation access patterns.
- Provide an ERD split into readable aggregate diagrams plus a cross-aggregate relationship catalog.
- Define transaction boundaries, cyclic-FK handling, and ordered migration groups for `DAT-002`.
- Record a contract-by-contract schema review.

## Out of scope

- SQLAlchemy model edits, Alembic setup/revisions, database profiles, repositories, or application compatibility code.
- Executing PostgreSQL, applying DDL, selecting extensions, or benchmarking query plans.
- Changing accepted entity semantics, lifecycle values, retention policy, public APIs, or authentication design.
- Redis/queue selection, artifact-store implementation, vector indexes, or graph database adoption.

## Existing code to reuse

- `backend/app/db/models.py` and `backend/app/db/session.py` are the verified SQLite baseline only; they are not production schema authority.
- Existing opaque string IDs and repository/index fields inform compatibility notes where they do not conflict with accepted contracts.
- `physical-schema-blueprint.md` supplies the accepted aggregate outline; the new physical schema adds the exact details required by `DAT-002`.

## Implementation sequence

1. Inventory accepted aggregates, identities, lifecycles, transaction boundaries, and required access patterns.
2. Fix shared PostgreSQL conventions and lifecycle check values.
3. Define each table with exact columns, keys, foreign keys, checks, and uniqueness.
4. Define named indexes and map every index to an API, worker, cleanup, activation, or evaluation query.
5. Draw aggregate ERDs and audit every cross-aggregate relationship against the table dictionary.
6. Define ordered migration groups, deferred cyclic foreign keys, SQLite compatibility boundaries, and DAT-002 handoff requirements.
7. Complete the schema review evidence and update status/navigation.

## Data/API compatibility and migration

This task changes documentation only. The design must preserve opaque public IDs and current local/test SQLite support while declaring PostgreSQL as the future production authority. `DAT-002` owns the baseline migration, supported-upgrade fixture, forward-recovery policy, and application compatibility implementation. No existing database is modified by this task.

## Failure, security, performance, and observability requirements

- Never store raw credentials, absolute host paths, hidden chain-of-thought, or unrestricted provider/source payloads.
- Credential columns store opaque secret-manager references or one-way token hashes only.
- Every repository-owned or versioned record has enforceable ownership FKs; JSON cannot hide query-critical identity, lifecycle, lease, range, or join fields.
- Lease fencing, cancellation, activation, deletion, idempotency, evidence retention, and audit invariants must be expressible through constraints plus documented transactions.
- Indexes must name their consumer and stable ordering; speculative indexes are forbidden.

## Required tests and commands

Run from the repository root:

```powershell
rg -n "^## |^### " docs/04-domain-and-data/postgresql-physical-schema.md docs/04-domain-and-data/postgresql-erd.md
rg -n "operator_principals|repositories|source_snapshots|import_sessions|index_jobs|job_attempts|index_versions|index_artifacts|files|symbols|endpoints|references|chunks|graph_nodes|graph_edges|validation_issues|capability_readiness|evidence|conversations|messages|agent_traces|evaluation_datasets|evaluation_runs|evaluation_results" docs/04-domain-and-data/postgresql-physical-schema.md docs/04-domain-and-data/postgresql-erd.md
git diff --check -- docs/04-domain-and-data/README.md docs/04-domain-and-data/database-design.md docs/04-domain-and-data/postgresql-physical-schema.md docs/04-domain-and-data/postgresql-erd.md docs/16-agent-tasks/persistence/DAT-001-postgresql-schema-and-erd.md docs/18-production-evidence/schema-design-review-report.md docs/project-status.md
git diff --name-only -- backend frontend tests storage
```

The final command must print no paths. Review evidence is recorded in `docs/18-production-evidence/schema-design-review-report.md`.

## Acceptance criteria

- The table dictionary names every production table and fixes every column's PostgreSQL type, nullability/default, and semantic owner.
- Every table has a primary key; every repository/index-scoped table has an ownership FK; every canonical observation has a unique repository/version/key constraint.
- One active index version, one incompatible running job, lease fencing, idempotency scope, same-version graph edges, evidence source ranges, and claim-to-citation support are explicitly enforceable.
- Every named index maps to at least one documented access pattern and includes a deterministic unique tie-breaker where pagination applies.
- The ERD contains every table and agrees with the foreign-key catalog; intentionally omitted high-volume event/payload relations are explained.
- Migration groups identify enum/check creation, tables, deferred cyclic FKs, partial unique indexes, and seed/config work in executable order.
- The review report traces all accepted data-model invariants to tables/constraints/transactions and records no unresolved P0 ambiguity.
- Only the allowed documentation paths change.

## Rollback

Revert the DAT-001 documentation commit. No runtime code, schema, database, or persisted data rollback is required.

## Documentation and evidence updates

Update domain/data navigation, database-design handoff, this task, project status, and `docs/18-production-evidence/schema-design-review-report.md`.

## Completion evidence

- The accepted physical design defines 35 production tables across access/audit, repository/import, durable jobs/index versions, code intelligence/graph, evidence/assistant, and evaluation aggregates.
- All versioned observations and cross-aggregate support relations use repository/index ownership; partial unique indexes and deferred constraints cover active version, active job, attempt fencing, and cyclic pointers.
- Twenty-four named indexes map to explicit API, worker, cleanup, graph, conversation, audit, and evaluation consumers; speculative text/vector indexes remain deferred.
- Five aggregate ERDs contain all 35 tables and a cross-aggregate composite-FK catalog.
- Required inventory searches passed, `git diff --check` passed, and no backend, frontend, test, fixture, storage, dependency, ORM, or migration path changed on 2026-07-13.
- Contract review and the DAT-002 handoff are recorded in `docs/18-production-evidence/schema-design-review-report.md`; no unresolved P0 design ambiguity remains.
