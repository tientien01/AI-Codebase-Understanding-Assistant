# ADR-0002: Reproducible Development Toolchain

Status: Accepted

Owner: Project maintainer

Last verified: 2026-07-13

Dependencies: `ADR-0001-production-foundations.md`, `../03-technology/adoption-process.md`

## Context

The verified baseline uses Python 3.11 for the backend and Node.js 24/npm 11 for the frontend, but the repository does not declare those runtimes or lock Python transitive dependencies. Root Pytest discovery also enters imported repositories under `storage/`. `FND-002` needs one reviewed toolchain decision before it can become executable.

## Decision

- Support Python `>=3.11,<3.12` for this delivery phase and declare `3.11` in `.python-version`.
- Keep `backend/requirements.txt` as the human-maintained direct dependency inventory.
- Use `uv==0.11.28` only as pinned development/CI tooling. Generate `backend/requirements-lock.txt` with a universal Python 3.11 resolution and hashes; install clean environments from that lock with `uv pip sync`.
- Support Node.js `>=24,<25` and npm `>=11,<12`; declare `24` in `.nvmrc`. Node 24 is the reviewed LTS line and matches the verified local major version. A future major change requires compatibility review and regenerated evidence.
- Keep `frontend/package-lock.json` as the authoritative npm lock and use `npm ci` for clean installs.
- Pin third-party CI actions to full commit SHAs and pin the installed `uv` version explicitly. CI caches are optional and must not be required for a clean install.

The canonical Python lock command is:

```powershell
uv pip compile backend/requirements.txt --python-version 3.11 --universal --generate-hashes --output-file backend/requirements-lock.txt
```

The canonical Windows clean-environment commands are:

```powershell
uv venv backend/.venv-clean --python 3.11
uv pip sync --python backend/.venv-clean/Scripts/python.exe backend/requirements-lock.txt
backend/.venv-clean/Scripts/python.exe -m pytest tests -q
```

## Alternatives considered

- `pip freeze` was rejected because it snapshots an existing environment rather than deterministically resolving the maintained direct requirements.
- `pip-tools` can produce a compatible requirements lock, but it would add a second Python packaging tool where pinned `uv` already provides universal resolution, hashes, environment creation, and exact sync.
- Moving all dependencies into a new project-native lock was deferred because `FND-002` must preserve the existing direct requirements inventory and avoid product dependency changes.
- Node 22 remains LTS, but Node 24 aligns with the verified environment and provides the longer forward support window for the first production delivery chain.

## Adoption assessment

- **Purpose and boundary:** `uv` is development/CI bootstrap and lock tooling only; it is not imported by the application or deployed as an application dependency.
- **License and maintenance:** the upstream project is actively maintained by Astral and distributed under MIT and Apache-2.0 licenses. The selected release supports Windows, Linux, and macOS.
- **Security:** use the pinned version, official release artifacts or the official setup action pinned by commit SHA, generated hashes, and no private index or credential input. Review generated files for URLs and local paths before commit.
- **Compatibility and transitive impact:** the universal lock targets Python 3.11 and preserves the existing direct dependency set. Any changed resolved package is a review failure, not an implicit upgrade.
- **Operational cost and observability:** CI records `uv --version`, Python, Node, and npm versions. Tool/bootstrap or resolution failure fails setup before application code runs; caches are optional.
- **Rollback:** remove the tool invocation and generated metadata/lock files. The pre-existing direct requirements remain available, so no application or data migration is required.

Official references: [uv locking environments](https://docs.astral.sh/uv/pip/compile/), [uv GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/), and [Node.js release status](https://nodejs.org/en/about/previous-releases).

## Consequences and enforcement

- Lock generation is an explicit review action; routine clean installs consume the committed lock without re-resolving it.
- Any changed resolved package version is reviewed as a dependency change and returns `FND-002` to draft unless separately authorized.
- CI verifies Python 3.11, Node 24, npm 11, lock-based clean installs, scoped Pytest collection, frontend lint, and the production build.
- The lock must not contain credentials, private index URLs, or local filesystem paths.

## Migration and rollback

`FND-002` adds the declarations and lock without changing application behavior. Rollback removes the new metadata and CI files and restores the previous manifests. No runtime data migration is involved.
