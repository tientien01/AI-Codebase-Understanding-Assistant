# Operator Access Recovery

Status: Implemented SEC-002 trusted-host procedure

Scope: single-node production operator password loss or credential compromise

## Preconditions

- Work locally on the trusted deployment host; do not expose this command through HTTP, CLI/MCP remote transport or automation logs.
- Configure the normal production `APP_ENV`, PostgreSQL `DATABASE_URL`, Redis/job settings, artifact root and explicit operator-access settings through the deployment secret mechanism.
- Confirm the database is reachable and exactly at the repository Alembic head.

## Rotate and revoke

```powershell
$env:APP_ENV='production'
backend\.venv\Scripts\python.exe backend/scripts/operator_recovery.py
```

Enter and confirm a new password only at the hidden prompt. The command stores a new `scrypt/v1` verifier, revokes every current browser session and named API token in one transaction, and appends `operator.recovery.rotate_password`. It prints only revoked record counts.

## Verify

1. Confirm every old session cookie and API token returns `401 AUTHENTICATION_REQUIRED`.
2. Log in with the new password and obtain a newly rotated session/CSRF pair.
3. Recreate only the named API tokens still required by trusted automation.
4. Review the safe recovery audit event locally; do not export credential values or hashes.

If the command reports that operator identity is not uniquely initialized, stop. Do not insert, delete or rewrite principal rows manually; restore the accepted database state or escalate through an authorized recovery task.
