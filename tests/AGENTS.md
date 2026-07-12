# Test Agent Rules

- Read the selected `ready` or `in_progress` task, linked contracts, fixture catalog, and current test inventory before editing. Root `AGENTS.md` rules continue to apply.
- Use small synthetic, secret-free fixtures; never use production repositories or real credentials.
- Test discovery must stay inside project test roots and must never collect or execute tests from imported repositories, storage, dependencies, build outputs, or archives.
- Test public behavior and invariants, not private implementation details without a strong reason.
- Parser/graph changes require golden facts, provenance, validation, and full/incremental equivalence coverage.
- Worker changes require restart, retry, duplicate delivery, cancellation, stale lease, and failed-publish tests.
- Retrieval/agent changes require deterministic regression datasets; exact/keyword/naive-vector/hybrid/agent comparisons where applicable; and positive, negative, ambiguous, stale, provider-outage, prompt-injection, budget, and insufficient-evidence cases.
- Evidence tests cover repository/index/access binding, source/range/hash validity, support/provenance, secrets, stale history, claim support, and cross-repository denial.
- Import/security tests cover traversal, duplicate normalized/case/Unicode paths, links, nested archives, ZIP bombs/quotas, Git SSRF/redirect/protocol/hooks/submodules/LFS, parser resource limits, log/trace leakage, deletion boundaries, and authorization.
- API changes require OpenAPI/schema drift, request ID, error envelope, authentication/authorization, idempotency, stable cursor, explicit version, range/projection limit, retryability, and degraded-capability tests.
- Schema changes require empty install, supported upgrade, constraints/indexes, drift, PostgreSQL integration, and declared rollback/forward-recovery tests.
- Frontend changes require applicable component/hook/API-mock, deep-link, async/degraded-state, accessibility, large-data/performance, and critical E2E coverage.
- Operations/deployment changes require health/readiness, dependency outage, disk/OOM/timeout, migration, backup/restore, rollback/forward-recovery, container, and smoke evidence declared by the task.
- Do not update golden outputs merely to make tests pass; explain and review semantic changes.
