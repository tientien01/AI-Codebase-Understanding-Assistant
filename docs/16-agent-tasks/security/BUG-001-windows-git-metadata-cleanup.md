---
id: BUG-001
title: Make bounded GitHub import robust on Windows and large-file repositories
status: blocked
priority: P0
phase: 7
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [SEC-001]
requirements: []
contracts:
  - docs/07-security/threat-model.md
  - docs/16-agent-tasks/security/SEC-001-import-acquisition-hardening.md
decisions: []
technology_docs: []
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
allowed_paths:
  - backend/app/services/ingestion/import_session_service.py
  - backend/app/services/ingestion/import_policy.py
  - tests/security/test_import_acquisition_security.py
  - docs/16-agent-tasks/security/BUG-001-windows-git-metadata-cleanup.md
  - docs/18-production-evidence/windows-git-import-cleanup-report.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - backend/app/api/**
  - backend/app/db/**
  - backend/migrations/**
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Git metadata removal succeeds when Git pack files carry the Windows read-only attribute.
  - A repository remains importable when individual files exceed the indexing limit; those files are skipped truthfully during preview.
  - File-count and aggregate-byte acquisition limits remain hard failures.
  - Cleanup remains bounded to the validated import-session root and does not follow invalid Git metadata links.
  - The focused acquisition-security and ingestion regression suites pass without network access.
evidence_outputs:
  - docs/18-production-evidence/windows-git-import-cleanup-report.md
---

# BUG-001 — Robust bounded GitHub import

## Objective

Fix public GitHub import where Windows read-only Git metadata or non-indexable large repository assets currently fail the entire preview.

## In scope

- Retry removal after making only the denied path writable.
- Reuse the same bounded removal behavior for failed import-session cleanup.
- Add a regression fixture containing a read-only Git pack index.
- Keep hard file-count and aggregate-byte acquisition quotas, while applying the per-file content limit at the existing scanner boundary so oversized files are reported as skipped instead of rejecting the repository.

## Out of scope

Arbitrary URL/code-host support, clone command changes, API schema changes, dependencies, storage migration, telemetry, and unrelated cleanup refactors. Additional code hosts require explicit adapters and SSRF-safe allowlists.

## Required tests and commands

```powershell
$env:APP_ENV='test'
backend\.venv\Scripts\python.exe -m pytest tests/security/test_import_acquisition_security.py tests/test_codebase_service.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

Tests use mocked Git execution and temporary directories; they must not access the network or execute imported source.

## Acceptance criteria

- A cloned tree containing a read-only `.git/objects/pack/*.idx` reaches import preview with `.git` removed.
- A cloned tree with an oversized source/data file reaches preview, reports the file as skipped, and retains supported files.
- Aggregate repository overflow still fails with `REPOSITORY_TOO_LARGE` and removes staging.
- Non-permission removal failures are not silently converted into success.
- Existing acquisition-security and service regressions pass.

## Rollback

Restore direct `shutil.rmtree` calls and remove the read-only regression fixture. No schema or dependency rollback is required.

## Blocker

The focused hotfix and non-evaluation backend suites pass, and live import progressed beyond metadata cleanup into preview preparation. Completion remains blocked by the pre-existing CRLF mismatch in the frozen evaluation fixture, which prevents the mandatory full backend gate from passing without an unrelated fixture normalization.
