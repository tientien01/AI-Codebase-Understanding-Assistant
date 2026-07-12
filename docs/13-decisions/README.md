# Architecture Decision Records

ADRs record why a production choice exists, alternatives, consequences, enforcement, migration, and rollback. Status is Proposed, Accepted, Superseded, Rejected, or Deprecated.

Initial accepted directions:

- Deterministic analysis before LLM inference.
- Evidence before answer claims.
- Immutable versioned index artifacts with atomic activation.
- PostgreSQL for production and SQLite for local/test.
- Durable external job execution instead of process-local threads.
- Canonical graph separated from bounded UI/query projections.

Queue implementation, reverse proxy, vector storage, graph database, agent framework, and advanced graph UI libraries remain undecided until their PoCs and triggers are satisfied.
