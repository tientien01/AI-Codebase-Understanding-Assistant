---
id: SEC-002
title: Enforce single-operator authentication, repository access, and audit
status: completed
priority: P0
phase: 7
owner: project-maintainer
last_verified: 2026-07-14
depends_on: [DAT-003]
requirements: []
contracts:
  - docs/07-security/threat-model.md
  - docs/07-security/specifications/risks-and-constraints.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/04-domain-and-data/postgresql-physical-schema.md
  - docs/04-domain-and-data/specifications/detailed-data-model.md
decisions: []
technology_docs:
  - docs/03-technology/stack-overview.md
baseline_docs:
  - docs/14-implementation-baseline/api-coverage.md
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
allowed_paths:
  - backend/app/core/config.py
  - backend/app/core/auth.py
  - backend/app/core/errors.py
  - backend/app/main.py
  - backend/app/api/dependencies.py
  - backend/app/api/v1/routes/auth.py
  - backend/app/schemas/auth.py
  - backend/app/schemas/api.py
  - backend/app/services/application/container.py
  - backend/app/services/security/**
  - backend/app/db/production_models/access.py
  - backend/migrations/versions/0002_operator_authentication.py
  - backend/scripts/operator_recovery.py
  - tests/security/test_auth_access_audit.py
  - tests/test_api_contract.py
  - tests/persistence/test_production_repository.py
  - tests/migrations/test_migrations.py
  - docs/04-domain-and-data/postgresql-physical-schema.md
  - docs/06-api-and-integrations/specifications/detailed-rest-api-contract.md
  - docs/14-implementation-baseline/api-coverage.md
  - docs/14-implementation-baseline/source-map.md
  - docs/14-implementation-baseline/test-inventory.md
  - docs/14-implementation-baseline/capability-baseline.md
  - docs/15-plans/phases/phase-7-security-and-operations.md
  - docs/16-agent-tasks/security/SEC-002-auth-access-audit.md
  - docs/17-runbooks/operator-access-recovery.md
  - docs/18-production-evidence/auth-access-audit-report.md
  - docs/06-api-and-integrations/artifacts/openapi-v1.json
  - docs/project-status.md
forbidden_paths:
  - backend/.env
  - backend/.env.*
  - frontend/**
  - storage/**
dependency_changes:
  allowed: false
  add: []
  remove: []
production_gates:
  - Production rejects the optional shared-token compatibility mode and requires an initialized operator credential boundary.
  - Bootstrap is one-time, password verifiers use fixed versioned scrypt parameters, and raw credentials never enter domain records, logs, errors, or audit details.
  - Browser sessions use opaque rotating cookies with absolute and idle expiry plus strict Origin and CSRF validation for mutations.
  - Named API tokens are shown once, stored only as salted hashes, individually expirable and revocable, and accepted only as Bearer credentials.
  - Repository-scoped requests validate the authenticated principal against repository ownership and return non-disclosing 404 denials.
  - Authentication lifecycle and authorization denials append privacy-safe audit events; audit records remain append-only.
  - Recovery revokes every session and API token through an explicit local operator command without exposing stored credential material.
evidence_outputs:
  - docs/18-production-evidence/auth-access-audit-report.md
---

# Task SEC-002 — Enforce single-operator authentication, repository access, and audit

## Context

The accepted production schema already contains principals, sessions, API tokens, repository ownership and append-only audit events, but the HTTP boundary still uses one optional shared token and permits a blank-token bypass. There is no bootstrap/login/session/token lifecycle, CSRF/origin enforcement, repository-owner denial, recovery command or authorization matrix.

## Objective

Replace production shared-token authentication with one deterministic single-operator boundary that supports one-time bootstrap, browser sessions, named API tokens, repository ownership checks, privacy-safe audit records and fail-closed recovery while preserving local development compatibility.

## In scope

- Versioned password/session/API-token hashing using the Python standard library and constant-time verification.
- One-time operator bootstrap, login, logout, session inspection and named token create/revoke endpoints.
- Server-side session cookie, absolute/idle expiry, rotation, strict Origin and double-submit CSRF checks for browser mutations.
- Bearer API-token authentication without browser-token storage or CSRF requirements.
- Repository path ownership authorization with non-disclosing denials and audit events.
- PostgreSQL access adapter over the accepted production access tables, a deterministic in-memory adapter for local/tests, and one additive password-verifier migration.
- Explicit revoke-all recovery command and documented retention/lifetime configuration.
- Negative authentication, CSRF, token lifecycle, ownership and redaction tests.

## Out of scope

Multi-user sharing/RBAC, email/password reset, OAuth/OIDC, frontend login UX, TLS/container delivery, rate limiting, deletion execution, audit export/UI, automated audit retention deletion, CLI/MCP feature commands, and broader per-service principal propagation beyond the HTTP repository ownership boundary.

## Existing code to reuse

- `operator_principals`, `operator_sessions`, `operator_api_tokens`, repository ownership and append-only `audit_events` production tables.
- The FastAPI `require_api_auth` router dependency and domain error envelope.
- The production composition root and PostgreSQL engine from `ProductionRepositoryStore`.
- The committed OpenAPI drift gate and migration upgrade/drift fixtures.

## Implementation sequence

1. Add the additive password-verifier schema field and versioned security configuration with production fail-closed validation.
2. Implement deterministic hashing, access-store ports, in-memory/PostgreSQL adapters and privacy-safe audit append.
3. Add bootstrap/session/token lifecycle APIs and cookie/CSRF/origin behavior.
4. Replace the production shared-token dependency with authenticated principal resolution and repository ownership authorization while retaining explicit local compatibility.
5. Add revoke-all recovery, negative matrices, OpenAPI evidence and baseline updates.

## Data/API compatibility and migration

Migration `0002_operator_authentication` adds a nullable `password_hash` to `operator_principals`; bootstrap atomically populates it before credentials are usable. Existing production rows remain uninitialized and fail closed until operator recovery/bootstrap completes. New `/api/v1/auth/*` endpoints are additive. Existing local/test blank-token behavior remains available only outside production; production no longer accepts `X-API-Key` or the shared `API_AUTH_TOKEN`.

## Failure, security, performance, and observability requirements

- Password hashes use `scrypt/v1` with `N=32768`, `r=8`, `p=1`, a random 16-byte salt and a 32-byte derived key.
- Session/API-token secrets contain at least 256 random bits. Stored values contain a versioned salt and digest only; lookup uses the opaque record ID carried in the presented credential.
- Authentication errors expose `AUTHENTICATION_REQUIRED`; repository-owner mismatch exposes `RESOURCE_NOT_FOUND`; CSRF/origin failure exposes `CSRF_VALIDATION_FAILED`.
- Authentication failure audit details contain controlled reason codes only, never passwords, cookies, CSRF values, bearer tokens, source content or host paths.
- Session last-seen updates are bounded and do not extend absolute expiry. Disabled principals and revoked/expired credentials fail closed.
- Audit retention is configuration/documentation in this task; deletion execution remains operational work.

## Required tests and commands

```powershell
$env:APP_ENV='test'
backend\.venv\Scripts\python.exe -m pytest tests/security/test_auth_access_audit.py tests/test_api_contract.py -q
backend\.venv\Scripts\python.exe -m pytest tests -q
docker compose -f compose.integration.yml up -d postgres
$env:TEST_POSTGRES_ADMIN_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres'
backend\.venv\Scripts\python.exe -m pytest tests/migrations -q
backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini check
docker compose -f compose.integration.yml down
git diff --exit-code -- backend/requirements.txt backend/requirements-lock.txt
git diff --check
```

The targeted and full suites use the local/test profile. Authentication tests use deterministic in-memory records and never log or persist raw credentials. Migration/drift tests use only the declared `aica_test_` PostgreSQL databases. Record results in `docs/18-production-evidence/auth-access-audit-report.md`.

## Acceptance criteria

- Bootstrap succeeds exactly once, persists only a password verifier, rotates session material, and audits success/failure safely.
- Valid login establishes the strict cookie/CSRF pair; invalid, expired, idle, revoked and disabled-principal sessions return the stable unauthenticated response.
- Browser mutations reject missing/mismatched Origin or CSRF; safe reads and valid Bearer tokens follow the declared policy.
- API token creation returns the raw value once; stored records cannot reconstruct it; expiry and revocation are enforced.
- A principal cannot observe or mutate another principal's repository ID and receives the same 404 surface as a missing repository; a safe denial audit is appended.
- Production settings reject blank/shared-token compatibility and missing explicit security lifetimes/bootstrap credential.
- Focused, full backend, migration, schema-drift, dependency-drift and whitespace gates pass.

## Rollback

Remove the auth router/service boundary and recovery command, restore the development dependency for all profiles, downgrade migration `0002`, remove the password verifier field, and return this task to `ready`. Existing shared-token local behavior remains the compatibility fallback; any issued sessions/tokens become unusable after rollback.

## Documentation and evidence updates

Update the physical schema and REST contract, API/source/test/capability baselines, Phase 7 status, operator recovery runbook, project status and authorization evidence. Do not claim RBAC, Internet exposure, TLS, rate limiting, audit-retention execution, Phase 7 exit or L3 readiness.

## Closing evidence

The focused auth/API gate passes 14 tests with one local PostgreSQL-profile skip; the mandatory full backend suite passes 302 with 31 integration-profile skips. PostgreSQL 18.4 migration plus auth integration passes 17 tests, including the populated `0001` to `0002` upgrade, append-only audit and raw-credential exclusion, and Alembic reports zero schema drift. Dependency and whitespace checks pass. The remaining frontend, TLS, rate, retention, RBAC and release boundaries are recorded in the evidence report.
