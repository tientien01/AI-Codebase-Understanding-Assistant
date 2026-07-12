# Runbook — `<condition>`

Status: Draft  
Owner:  
Last exercised:  
Related alerts/dashboards:  
Related components/contracts:

## Trigger and impact

- Detection signal:
- User-visible impact:
- Data/integrity risk:
- Capabilities affected:

## Preconditions and safety

- Required access:
- Backup/snapshot requirement:
- Commands/actions that must not be run:
- Secret/redaction considerations:

## Diagnosis

Use bounded, read-only checks first. Record request, repository, job, index version, release and timestamps without copying secrets.

## Containment

List the smallest reversible action that stops further harm while preserving authoritative state and evidence.

## Recovery

Number each exact action, expected output, failure branch, and rollback/forward-recovery choice. Never reconstruct authoritative state from Redis, logs, or an unvalidated artifact.

## Verification

- Health/readiness checks:
- Data/index consistency checks:
- User-flow smoke test:
- Telemetry recovery:

## Cleanup and follow-up

- Temporary artifacts/leases:
- Incident/evidence location:
- Corrective task/ADR:
- Required regression test:
