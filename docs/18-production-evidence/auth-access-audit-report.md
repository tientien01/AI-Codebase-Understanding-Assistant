# SEC-002 Authentication, Access, and Audit Evidence

Status: Complete for SEC-002 scope

Task: `SEC-002`

Observed: 2026-07-14

## Implemented boundary

- One-time bootstrap initializes exactly one operator password verifier, including a migrated single uninitialized principal, and then disables itself.
- Passwords use `scrypt/v1` (`N=32768`, `r=8`, `p=1`, 16-byte salt, 32-byte key). Sessions and API tokens use at least 256 random bits and store versioned salted SHA-256 verifiers behind opaque record IDs.
- Browser sessions have absolute and idle expiry, revocation and strict production cookies. Mutations require an allowlisted exact Origin and session-bound CSRF token.
- Named Bearer tokens are shown once, individually bounded by expiry/revocation and never accepted from `X-API-Key` in production.
- Repository path requests compare the authenticated principal with `owner_principal_id`; missing and foreign IDs return the same safe 404 and append a controlled denial audit.
- Trusted-host recovery rotates the password verifier and transactionally revokes every session/token without printing secrets.

## Verification

| Gate | Result |
| --- | --- |
| Focused auth plus API contract | Passed: 14 tests; 1 PostgreSQL-profile skip; 2 existing/dependency warnings |
| Mandatory full backend suite | Passed: 302 tests; 31 integration-profile skips; 3 existing/dependency warnings |
| PostgreSQL migration plus auth integration | Passed: 17 tests; 2 existing/dependency warnings |
| Alembic upgrade and zero schema drift | Passed: `0001_production_baseline -> 0002_operator_authentication`; no new upgrade operations |
| Dependency drift | Passed: no requirements or lock changes |
| Diff whitespace validation | Passed |

The tests inspect stored records and audits to confirm that passwords, bootstrap credentials, session cookies, CSRF values and raw API tokens are absent. Authorization denial uses the same `404 RESOURCE_NOT_FOUND` response for foreign and missing repository IDs.

## Remaining boundaries

This evidence does not establish multi-user sharing/RBAC, frontend login UX, TLS/container exposure, request/rate/provider quotas, automated audit retention/deletion, audit export UI, parser resource isolation, content secret scanning, deletion drills, or Phase 7/L3 release qualification.
