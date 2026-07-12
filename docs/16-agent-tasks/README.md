# Agent Task System

Only tasks marked `ready` or `in_progress` authorize implementation. Tasks are created just-in-time from accepted plans to avoid stale speculative instructions.

## Status lifecycle

`draft → ready → in_progress → completed`; use `blocked` only when the blocking condition and required decision are recorded. Only the project owner or an explicitly authorized documentation/governance task may promote a task to `ready`.

## Readiness checklist

Before a task becomes `ready`, it has one verifiable outcome, satisfied dependencies, exact allowed/forbidden paths, linked requirements/contracts/ADRs, compatibility and rollback rules, concrete test commands, acceptance criteria, and evidence destinations. Discovery placeholders are not permitted in a ready task.

Recommended phase directories mirror `15-plans/`: foundation, persistence, durable-indexing, intelligence, retrieval-agent, production-ux, operations-security, release.

Execution flow:

```text
Read task → verify dependencies → read linked contracts/ADR/technology/baseline
→ inspect existing source/tests → implement only allowed scope
→ run commands → record evidence → update baseline/docs → complete
```

The task register is planning metadata, not authorization. If source reality invalidates a ready task, stop and return it to `draft` or amend it through the owning plan rather than expanding scope silently.
