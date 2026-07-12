# Technology and Dependency Adoption Process

## Flow

`measured requirement → candidate assessment → time-boxed PoC → ADR → migration plan → authorized tasks → verification → adopted stack`.

## Candidate assessment

Record the current limitation, alternatives, security/license/maintenance, operational cost, compatibility, data migration, lock-in, failure modes, observability, rollback, and measurable accept/reject criteria.

## Agent authorization

Tasks that change dependencies declare exact packages, manifests, purpose, accepted ADR, install/configuration steps, required lockfile, tests, deployment changes, and removal rollback. Agents may not browse for and install alternatives during implementation unless the task is explicitly a PoC.

## Upgrade policy

- Patch: automated only when all gates pass.
- Minor: compatibility review and regression suite.
- Major: migration plan; ADR when architecture/behavior changes.
- Security: expedited but still tested and recorded.
- Never use floating production versions.

## Removal

Deprecation specifies replacement, callers, data/config migration, compatibility window, removal test, and rollback. Removing the process-local indexing thread and manual schema patch are mandatory production migrations.
