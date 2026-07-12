# Definition of Done

Status: Accepted  
Authority: Task and phase completion  
Owner: Project maintainer  
Last verified: 2026-07-12

## Task done

A task is complete only when:

- its approved scope and acceptance criteria are satisfied;
- required tests and commands pass;
- behavior changes have tests;
- affected contracts, baseline, status, and user/operator docs are updated;
- required evidence is stored or linked;
- security, failure, compatibility, and rollback behavior are accounted for;
- no placeholder or undocumented critical dependency was added;
- the task status is changed to `completed` after verification.

Passing unit tests alone does not complete a task.

## Phase done

A phase is complete only when every exit gate in its canonical phase plan is supported by evidence. Optional tasks may remain open only when the plan explicitly states that they do not block the outcome.

## Release done

A release is complete only at a declared level from `release-levels.md`. L3 additionally requires every gate in `definition-of-production-ready.md` and `18-production-evidence/release-checklist.md`.

## Reopening work

If later verification disproves an acceptance claim, reopen the task or create a corrective task, mark affected evidence superseded, update `project-status.md`, and do not retain the higher readiness claim.
