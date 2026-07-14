---
id: SEC-001
title: Enforce quota-bound archive, folder, and public Git acquisition
status: completed
priority: P0
phase: 7
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [JOB-003]
requirements: []
contracts:
  - docs/07-security/threat-model.md
  - docs/07-security/specifications/risks-and-constraints.md
  - docs/04-domain-and-data/specifications/detailed-storage-design.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
decisions: []
technology_docs:
  - docs/02-system-architecture/deployment-and-capacity.md
baseline_docs:
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/core/config.py
  - backend/app/services/ingestion/archive_service.py
  - backend/app/services/ingestion/import_policy.py
  - backend/app/services/ingestion/import_session_service.py
  - backend/app/services/ingestion/upload_service.py
  - backend/app/services/ingestion/streaming_upload_service.py
  - tests/security/**
  - tests/test_codebase_service.py
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-7-security-and-operations.md
  - docs/16-agent-tasks/security/SEC-001-import-acquisition-hardening.md
  - docs/18-production-evidence/import-acquisition-security-report.md
  - docs/project-status.md
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
  - Archive plans reject traversal, links, special files, normalized collisions, excessive depth, entries, expanded bytes, per-file bytes, and compression ratios before unsafe writes.
  - Archive extraction counts actual streamed bytes and removes the isolated session root after every failed or empty acquisition.
  - Folder acquisition rejects unsafe and normalized-duplicate paths and enforces configurable total file and byte quotas with failed-session cleanup.
  - Public Git accepts only canonical credential-free HTTPS GitHub repository URLs and safe refs, disables redirects, prompts, hooks, submodules, LFS smudging, and non-HTTPS protocols, and uses shallow bounded execution.
  - Git acquisition validates the resulting tree against the same file/byte/path quotas, removes Git metadata, and cleans the isolated session root on timeout, failure, or quota rejection.
  - Errors expose stable codes and safe messages without host paths, credentials, command output, or imported content.
evidence_outputs:
  - docs/18-production-evidence/import-acquisition-security-report.md
---

# Task SEC-001 — Enforce quota-bound archive, folder, and public Git acquisition

## Context

The current ingestion boundary rejects basic ZIP traversal and duplicate paths, skips nested archives and secret-like files, and restricts Git URLs to GitHub. It does not yet enforce the complete accepted archive/folder tree quotas, reject link and special-file ZIP entries, normalize Unicode collisions, harden the Git subprocess, validate a cloned tree before preview, or guarantee cleanup for every failed acquisition.

## Objective

Make ZIP, folder, and public Git acquisition fail closed inside repository-owned staging with deterministic quotas, safe errors, hardened Git execution, and an adversarial regression suite covering threat controls `T-IMP-01`, `T-IMP-02`, and `T-GIT-01`/`T-GIT-02`.

## In scope

- A shared deterministic import-path identity and tree-quota policy reused by ZIP, folder, and cloned Git sources.
- ZIP link/special-file, Unicode/case collision, depth, entry, ratio, declared-size, and streamed-size enforcement.
- Folder duplicate-path, file-count, per-file, and aggregate-byte enforcement.
- Canonical public GitHub URL/ref validation and a non-interactive, HTTPS-only, no-redirect, shallow clone command with hooks, submodules, and LFS disabled.
- Post-clone tree validation, Git metadata removal, safe error mapping, and idempotent staging cleanup.
- Focused adversarial and existing ingestion regression tests.

## Out of scope

Authentication/authorization/audit (`SEC-002`), API wire-schema migration, rate limiting, parser process isolation, secret-content scanning, provider controls, deletion/retention scheduling, container/network namespaces, telemetry, deployment, dependency/SBOM scanning, and production capacity benchmark thresholds.

## Existing code to reuse

- `ArchiveService` path containment, skip-record, extension, and configured archive limits.
- `StreamingUploadService` bounded chunked writes and partial-file cleanup.
- `UploadService` folder path filtering.
- `ImportSessionService` isolated session roots, preview records, and stable `DomainError` mapping.

## Implementation sequence

1. Centralize normalized relative-path identity, link/special-file checks, and tree quota accounting in the ingestion boundary.
2. Validate ZIP plans completely, then enforce actual streamed-byte limits while extracting.
3. Apply duplicate, count, and aggregate quotas to folder uploads and clean every failed session.
4. Canonicalize GitHub inputs, validate refs, harden the clone environment/options, validate the resulting source tree, and clean failure state.
5. Add adversarial tests and run the focused and full backend regressions.
6. Record exact evidence and update the implementation baseline without claiming container/network or release qualification.

## Data/API compatibility and migration

No database migration or intentional successful-response shape change. Previously accepted unsafe archives, duplicate-normalized folder paths, unsafe Git refs, or over-quota Git/folder trees now fail with stable `400`, `413`, or `504` domain errors. Current configured limits remain the compatibility defaults; this task does not invent production capacity-class acceptance.

## Failure, security, performance, and observability requirements

- Perform metadata/path validation before archive writes and stop streaming immediately when actual bytes exceed the declared policy.
- Never include raw URL credentials, Git stderr/stdout, imported content, or resolved host paths in client-visible errors.
- Remove only a resolved session root proven to be under the configured upload root; cleanup is idempotent.
- Avoid loading whole uploaded files or archives into memory.
- Git subprocesses are non-interactive and bounded by a configurable timeout; broader OS/container resource and network isolation remains an `OPS-002` gate.
- Preview activity may report safe counts and reason codes only.

## Required tests and commands

```powershell
$env:APP_ENV='test'
backend\.venv\Scripts\python.exe -m pytest tests/security/test_import_acquisition_security.py tests/test_codebase_service.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
git diff --check
```

Run in the local test profile using temporary directories and mocked Git execution. The focused suite must not access the network or execute imported source. Record results in `docs/18-production-evidence/import-acquisition-security-report.md`.

## Acceptance criteria

- Adversarial ZIP cases cover traversal, link/special entries, Unicode/case collisions, nested archives, depth, entry count, declared and actual expanded bytes, and compression ratio.
- Folder cases cover traversal, normalized duplicates, file count, per-file bytes, aggregate bytes, and cleanup after rejection.
- Git cases prove URL/ref rejection, exact hardened command/environment constraints, timeout/failure cleanup, metadata removal, and post-clone quota rejection without real network access.
- Existing import preview, confirmation, duplicate-detection, cancellation, secret-path filtering, and API contract tests remain green.
- Full backend tests pass and the evidence report states the remaining parser, secret-content, container/network, rate, auth, and capacity/release gaps.

## Rollback

Restore the prior ingestion services and configuration defaults, remove the focused security suite and evidence report, and return the task to `ready`. No persisted schema or dependency rollback is required; rejected temporary sessions are non-authoritative.

## Documentation and evidence updates

On completion, update the source map, test inventory, capability baseline, Phase 7 plan, project status, this task, and the import acquisition security report. Do not claim Phase 7 or L3 completion.

## Current verification state

Implementation, documentation, and mandatory verification are complete. The focused gate passes 49 tests, the full backend suite passes 294 tests with 29 integration-profile skips, and `git diff --check` passes. The synthetic evaluation fixture was restored from checkout CRLF to its Git-index LF bytes so its declared content hashes validate; no dataset record, manifest, threshold, or gate was changed or bypassed.
