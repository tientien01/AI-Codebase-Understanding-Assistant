# Production Runbooks

Required runbooks before release: failed deployment, failed migration, stuck/stale index job, validation failure, broker/database/artifact/provider unavailable, backup restore, storage exhaustion, and security incident.

Every runbook contains symptoms, impact, safe diagnostics, recovery, integrity checks, rollback/escalation, and post-incident verification. It must never instruct broad deletion or expose credentials.

Create each runbook from `runbook-template.md`. A runbook becomes production evidence only after its steps are exercised on the release topology and the drill report is linked.

Development guidance is available in `development-setup.md` and `local-troubleshooting.md`. These documents describe the current local profile and must not be mistaken for L3 deployment/incident runbooks.
