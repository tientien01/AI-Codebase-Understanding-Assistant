---
id: FND-002
title: Establish reproducible Python and Node project metadata
status: draft
priority: P0
phase: 1
owner: unassigned
last_verified: 2026-07-12
depends_on: [DOC-002]
requirements: []
contracts:
  - docs/12-engineering/README.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
technology_docs:
  - docs/03-technology/stack-overview.md
  - docs/03-technology/adoption-process.md
allowed_paths:
  - backend/pyproject.toml
  - backend/requirements.txt
  - backend/requirements-lock.txt
  - frontend/package.json
  - frontend/package-lock.json
  - .python-version
  - .nvmrc
  - pytest.ini
  - .github/workflows/ci.yml
  - docs/**
forbidden_paths:
  - backend/app/**
  - frontend/src/**
  - tests/fixtures/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Clean installs use declared runtimes and locked dependency graphs.
  - Pytest collects only project tests and never imported repositories.
  - Existing backend behavior and frontend production build remain unchanged.
evidence_outputs:
  - docs/18-production-evidence/development-install-report.md
---

# Task FND-002 — Establish Reproducible Project Metadata

## Context

The backend has an unpinned `requirements.txt`, no Python project metadata/version declaration, and no pytest discovery configuration. The frontend has a lockfile but no declared Node engine/version. Root pytest currently enters untrusted imported repositories.

## Objective

Define supported development runtimes, lock the existing dependency set without adding/upgrading product dependencies, scope test discovery, and add a minimal CI install/test/lint/build workflow.

## In scope

- Select and document one Python locking mechanism using the accepted technology adoption process.
- Add `backend/pyproject.toml` for project/test/tool metadata without moving application code.
- Preserve human-maintained direct requirements separately from a deterministic transitive lock.
- Declare supported Python 3.11 and a reviewed Node/npm range.
- Add `pytest.ini` or canonical pyproject pytest configuration with `testpaths = tests` and ignored runtime/dependency/build paths.
- Add minimal CI jobs for clean backend install/tests and frontend `npm ci`, lint and build.

## Out of scope

- Adding, removing, or upgrading runtime/dev dependencies.
- Fixing the four existing frontend lint defects; either a prerequisite task must fix them or this task remains blocked from a green CI gate.
- Changing runtime code, API behavior, schemas, database migrations, or deployment containers.

## Existing code to reuse

- `backend/requirements.txt` as the current direct dependency inventory.
- `frontend/package.json` and `frontend/package-lock.json` as the Node manifest/lock baseline.
- The verified command/results in `docs/14-implementation-baseline/verification-report.md`.

## Implementation sequence

1. Review licenses, supported Python/Node versions and the existing resolved virtualenv/package lock.
2. Record and approve the Python lock-tool decision; update this task with exact generation/check commands before promotion to `ready`.
3. Add metadata/version/test-discovery files and generate the lock from existing constraints only.
4. Recreate clean backend/frontend environments and run all gates.
5. Add CI using the exact clean-install commands and store an install report.

## Data/API compatibility and migration

No runtime data/API change. Dependency resolution must reproduce current compatible behavior. Any forced package version change returns this task to draft and requires explicit dependency authorization.

## Failure, security, performance, and observability requirements

- Lock generation must not read credentials or include private indexes/tokens.
- Test discovery must exclude `storage/`, archives, dependencies, build outputs and imported repositories.
- CI uses minimal permissions and no provider secrets.
- Cache is an optimization only; clean install without cache remains supported.

## Required tests and commands

Exact Python lock commands remain a blocker until the lock mechanism is approved. Mandatory outcomes:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
npm.cmd ci
npm.cmd run lint
npm.cmd run build
```

CI must demonstrate that an unscoped pytest invocation still collects only configured project tests.

## Acceptance criteria

- Supported Python and Node versions are machine-readable and documented.
- Python direct and transitive dependencies are deterministic from a clean environment.
- `npm ci` uses the committed lock without mutation.
- No test under `storage/` is collected.
- 52 current backend tests pass; frontend lint/build gates pass after the known lint prerequisite is resolved.
- No application behavior or product dependency set changes.

## Rollback

Remove the added metadata/CI files and restore manifests/locks. No data migration is involved.

## Documentation and evidence updates

Update development setup, baseline, stack profiles, task status, project status and the development install report.

## Promotion blockers

- Choose and accept the Python lock mechanism and exact file format.
- Decide the supported Node LTS range rather than adopting the locally observed Node 24 automatically.
- Resolve or separately task the four current frontend lint errors so a new mandatory CI gate is not knowingly red.
