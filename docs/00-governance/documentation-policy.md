# Documentation Policy

Normative and task documents must declare: title, status, authority, owner, dependencies, related source, related tests, and last verification date.

Rules:

- One concept has one normative home; other documents link to it.
- Target design and current implementation are never mixed without explicit labels.
- Mermaid/DBML text is the diagram source; screenshots are supporting assets only.
- Code changes update affected baseline and contracts in the same task.
- Completed plans move to `completed/` only after baseline and evidence are updated.
- Archived documents are preserved but marked historical.
- Overview documents route readers and state invariants; they do not duplicate detailed field/endpoint/page specifications.
- Relative links are preferred inside `docs/` and must resolve in documentation validation.
- New accepted documents use UTF-8, include a last-verification date, and identify their owning authority.
- `project-status.md` changes only from verified baseline, task, or evidence changes.

## Review triggers

Review the owning document when a requirement, ADR, API/schema, dependency, capability, task gate, benchmark threshold, deployment topology, security boundary, or runbook changes. A completed task updates every affected target/baseline/evidence link in the same change.
