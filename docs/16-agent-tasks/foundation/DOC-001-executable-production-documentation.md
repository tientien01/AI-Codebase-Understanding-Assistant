---
id: DOC-001
title: Establish executable production documentation
status: completed
priority: P0
depends_on: []
requirements: []
contracts:
  - docs/00-governance/documentation-policy.md
  - docs/00-governance/source-of-truth.md
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
  - Documentation navigation is unambiguous.
  - Delivery phases have explicit entry and exit gates.
  - Initial implementation tasks are authorized only through task files.
---

# Task DOC-001 — Establish Executable Production Documentation

## Context

The repository has detailed target specifications and a verified implementation baseline, but it lacks an executable layer connecting product goals, release levels, phase gates, and ready tasks. Repeated roadmap summaries also make the next action difficult to identify.

## Objective

Turn `docs/` into the controlling system for incremental delivery from the current baseline to a single-node self-hosted production release.

## In scope

- Add current status, release levels, product positioning, scope, success metrics, architecture overview, capability model, failure model, and phased delivery plans.
- Consolidate roadmap navigation and remove unnecessary repetition from overview files.
- Update governance, traceability, task workflow, and production evidence guidance.
- Define the first draft implementation tasks without changing application source.

## Out of scope

- Backend, frontend, test, schema, dependency, or deployment changes.
- Claiming that any planned production capability is already implemented.
- Rewriting detailed specifications when a canonical specification already exists.

## Existing code to reuse

Not applicable. Reuse existing normative specifications, ADRs, baseline reports, and task IDs.

## Implementation sequence

1. Establish top-level status and reading paths.
2. Define release levels and measurable product boundaries.
3. Add architecture and operational control documents.
4. Replace the flat roadmap view with gated phase plans.
5. Add initial draft task specifications and update traceability.
6. validate links, encoding, and duplication.

## Data/API compatibility and migration

No runtime data or API changes. Existing detailed specifications remain authoritative unless an owning README explicitly points to a newer document.

## Failure, security, performance, and observability requirements

- Do not include secrets or inspect credential files.
- Do not weaken current security or production gates.
- Preserve the distinction between target, baseline, plan, task, and evidence.

## Required tests and commands

- Enumerate Markdown links and verify local targets exist.
- Search non-archive docs for mojibake and obsolete navigation.
- Review `git diff --check` and the final docs-only diff.

## Acceptance criteria

- A contributor can determine current status, target release, active phase, next task, and exit gate from the documentation hub.
- Each delivery phase has outcome, scope, dependencies, entry criteria, exit evidence, and task IDs.
- No source change is authorized by this documentation task.
- Duplicate roadmap authority is replaced by links to one canonical phase plan.

## Rollback

Revert the documentation-only commit. Runtime behavior and persisted data are unaffected.

## Documentation and evidence updates

This task is itself the documentation change. Completion evidence is the validated docs tree and diff recorded in the task status.

## Completion evidence

Verified on 2026-07-12:

- all non-archive backticked Markdown document references resolve;
- all Markdown links resolve;
- non-archive Markdown is valid UTF-8 with one H1 and balanced code fences;
- no non-archive mojibake pattern or stale promoted-document path remains;
- `git diff --check -- docs` reports no whitespace error for tracked changes;
- application source, tests, dependencies, and runtime data were not modified by this task.
