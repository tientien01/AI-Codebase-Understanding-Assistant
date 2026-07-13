---
id: FND-002
title: Establish reproducible Python and Node project metadata
status: completed
priority: P0
phase: 1
owner: project-maintainer
last_verified: 2026-07-13
depends_on: [DOC-003, FND-005]
requirements: []
contracts:
  - docs/12-engineering/README.md
decisions:
  - docs/13-decisions/ADR-0001-production-foundations.md
  - docs/13-decisions/ADR-0002-reproducible-development-toolchain.md
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

The backend has an unpinned `requirements.txt`, no Python project metadata/version declaration, and no pytest discovery configuration. The frontend has a lockfile but no declared Node engine/version. Root pytest currently enters untrusted imported repositories. `ADR-0002` resolves the lock mechanism and runtime ranges; `FND-005` owns the existing frontend lint prerequisite.

## Objective

Define supported development runtimes, lock the existing dependency set without adding/upgrading product dependencies, scope test discovery, and add a minimal CI install/test/lint/build workflow.

## In scope

- Apply the accepted `uv==0.11.28` lock mechanism from `ADR-0002`.
- Add `backend/pyproject.toml` for project/test/tool metadata without moving application code.
- Preserve human-maintained direct requirements separately from a deterministic transitive lock.
- Declare Python `>=3.11,<3.12`, Node.js `>=24,<25`, and npm `>=11,<12`.
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

1. Verify `FND-005` is completed and confirm the existing direct dependency and package-lock inventories are unchanged.
2. Add metadata/version/test-discovery files and generate the universal hashed Python 3.11 lock from existing constraints only.
3. Recreate clean backend/frontend environments and run all gates.
4. Add CI using pinned third-party actions and the exact clean-install commands.
5. Re-run lock generation without upgrades, verify no diff, and store the install report.

## Data/API compatibility and migration

No runtime data/API change. Dependency resolution must reproduce current compatible behavior. Any forced package version change returns this task to draft and requires explicit dependency authorization.

## Failure, security, performance, and observability requirements

- Lock generation must not read credentials or include private indexes/tokens.
- Test discovery must exclude `storage/`, archives, dependencies, build outputs and imported repositories.
- CI uses minimal permissions and no provider secrets.
- Cache is an optimization only; clean install without cache remains supported.

## Required tests and commands

Run from the repository root with `uv==0.11.28`, Python 3.11, Node 24, and npm 11:

```powershell
uv --version
uv pip compile backend/requirements.txt --python-version 3.11 --universal --generate-hashes --output-file backend/requirements-lock.txt
uv venv backend/.venv-clean --python 3.11
uv pip sync --python backend/.venv-clean/Scripts/python.exe backend/requirements-lock.txt
uv pip check --python backend/.venv-clean/Scripts/python.exe
backend/.venv-clean/Scripts/python.exe -m pytest tests -q
backend/.venv-clean/Scripts/python.exe -m pytest -q
Set-Location frontend
node --version
npm.cmd --version
npm.cmd ci
npm.cmd run lint
npm.cmd run build
```

Return to the repository root, record the lock hash, re-run the lock command, then verify that its content is unchanged:

```powershell
$lockHash = (Get-FileHash backend/requirements-lock.txt -Algorithm SHA256).Hash
uv pip compile backend/requirements.txt --python-version 3.11 --universal --generate-hashes --output-file backend/requirements-lock.txt
if ((Get-FileHash backend/requirements-lock.txt -Algorithm SHA256).Hash -ne $lockHash) { throw 'Python lock regeneration changed the committed resolution.' }
git diff --exit-code -- frontend/package-lock.json
git diff --check -- backend/pyproject.toml backend/requirements.txt backend/requirements-lock.txt frontend/package.json frontend/package-lock.json .python-version .nvmrc pytest.ini .github/workflows/ci.yml docs
```

CI must use the same lock/install/test/lint/build sequence, pin third-party actions to full commit SHAs, pin `uv` to `0.11.28`, and demonstrate that an unscoped Pytest invocation collects only configured project tests.

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

## Promotion resolution

- `FND-005` completed on 2026-07-13 with green targeted-test, lint, and build evidence. The lock mechanism, file format, runtime ranges, and exact local commands are accepted in `ADR-0002`; no discovery placeholder remains.

## Local verification evidence

Verified on 2026-07-13 with Python 3.11.9, `uv==0.11.28`, Node 24.14.0, and npm 11.9.0: clean Python sync installed 107 packages with zero baseline version drift; `uv pip check` passed; targeted and root Pytest each passed 52 tests with one expected warning; canonical lock regeneration was hash-stable; `npm ci` preserved its lock hash; 4 frontend tests, lint, and production build passed; and the pinned CI YAML parsed with backend/frontend jobs. See `docs/18-production-evidence/development-install-report.md`.

## Completion evidence

- Commit `fe91e5fe729b446ab989d03bcc81d3d711846669` passed both mandatory jobs in the immutable [push workflow run](https://github.com/tientien01/AI-Codebase-Understanding-Assistant/actions/runs/29223127315) and the independent [pull-request workflow run](https://github.com/tientien01/AI-Codebase-Understanding-Assistant/actions/runs/29223163997) on 2026-07-13.
- The backend job installed the hashed Python lock, validated dependencies, passed targeted and root-scoped Pytest, and reproduced the lock. The frontend job passed locked install, targeted tests, lint, and production build.
- All acceptance criteria and required production evidence are satisfied. `FND-002` completed on 2026-07-13.
