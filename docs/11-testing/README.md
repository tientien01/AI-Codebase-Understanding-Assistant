# Test Strategy

`fixture-catalog.md` owns the synthetic repository fixture inventory and required future fixture matrix. Current executable test coverage and command results are recorded in `14-implementation-baseline/test-inventory.md`.

Required layers:

- Unit: parsers, IDs, filters, ranking, state machines, validation, security rules.
- Integration: database repositories, migrations, queue/worker recovery, artifact storage, index activation, provider adapters.
- Contract: OpenAPI, artifacts, parser output, graph, tools, errors, capability readiness.
- E2E: import → index → explore/search/chat → evidence → re-index/staleness → impact/evaluation.
- Security: archive/Git attacks, prompt injection, secrets, auth boundaries, rate/size limits.
- Performance: reference repository sizes, graph projection, retrieval, index throughput, frontend layout.
- Resilience: API/worker/database/broker/storage/provider restart and failure.

Golden fixtures are small, synthetic, versioned, secret-free, and include expected files, symbols, endpoints, relations, graph paths, citations, and incremental changes.

`specifications/detailed-testing-plan.md` provides the detailed unit, integration, frontend, evaluation, E2E, fixture, command, pass-criteria, canonical inventory, resolver, graph, fingerprint, activation, equivalence, tour, and readiness test matrix.
