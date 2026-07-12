# Documentation Agent Rules

Root `AGENTS.md` authority and task-authorization rules continue to apply. Documentation-only changes require a selected `ready` or `in_progress` task unless the project owner explicitly authorizes a narrowly scoped governance/documentation correction.

- Read `README.md`, `00-governance/source-of-truth.md`, `00-governance/documentation-policy.md`, the selected task, and only the owning contracts/baseline/evidence needed for the change.
- Preserve the distinction between accepted target, verified baseline, plan, executable task, production evidence, research, and historical/archive content.
- One concept has one normative owner. Overview/README files route and summarize; they do not duplicate detailed fields, endpoint shapes, state machines, or page contracts.
- Do not create an “old design plus Production Update” document. Rewrite the current target coherently and preserve superseded history under `99-archive/` only when history has value.
- Research and archive are informative only. A technology or feature enters the target through accepted requirements/contracts/ADR/plan/task, not by being mentioned in research.
- Do not claim `accepted` means implemented, `implemented` means verified, or a local demo means L3-ready. Update baseline/status/evidence only from source, tests, commands, or release artifacts.
- Normative and task documents declare title, status, authority, owner, dependencies, related source, related tests, and last verification date. Use `not applicable` with a reason rather than silently omitting a required field.
- Keep canonical vocabulary aligned: repository lifecycle, import session, job/attempt, index lifecycle, source freshness, and capability readiness are separate. Capability states are `ready`, `limited`, `unavailable`, `failed`, or `stale`.
- Keep Retrieval Candidate, Evidence, Citation, and Claim distinct. Preserve repository/index binding, provenance/support type, coverage, truncation, and insufficient-evidence semantics.
- Technology descriptions follow `03-technology/` and accepted ADRs. Do not restore SQLite/Chroma/LangGraph/private-Git/graph-DB/vector-DB candidates as production defaults.
- Do not invent numeric capacity, performance, quality, cost, or SLO thresholds. Record the metric, reference environment, benchmark/evidence owner, and acceptance process until measured values are approved.
- Stay within the task's `allowed_paths`; do not create review reports, matrices, plans, ADRs, tasks, or evidence files unless the task explicitly requires them.
- After editing, reread every changed file and validate UTF-8, one H1, balanced fences, local links/references, terminology, authority, target/baseline separation, task/plan scope, and whitespace. Run the exact documentation validation commands declared by the task.
