# Production Gap Analysis

| Priority | Gap | Target | Exit evidence |
| --- | --- | --- | --- |
| P0 | Documentation authority and source boundaries | Governance/contracts/tasks | Docs checks and approved blueprint |
| P0 | Manual schema evolution/SQLite-only | PostgreSQL + Alembic profiles | Migration/drift/restore tests |
| P0 | Process-local index threads | Durable idempotent worker | Restart/retry/cancel/recovery E2E |
| P0 | Mutable aggregate index state | Immutable artifacts + atomic publish | Failure/rollback/equivalence tests |
| P0 | Import trust risks | Isolated quota-bound ingestion | Security suite/threat evidence |
| P1 | Route/schema/facade hotspots | Domain application boundaries | Boundary tests and smaller modules |
| P1 | Parser pipeline overlap | Canonical adapter/IR/resolver contract | Golden/equivalence tests |
| P1 | In-memory retrieval limits | Versioned retrievers/ranker/evidence selector | Retrieval benchmark/load report |
| P1 | Monolithic frontend state | Router + Query + feature state | E2E/deep-link/error-state tests |
| P1 | Lightweight graph UX | Bounded projections, evidence, tours/diff | Large graph/performance/UX tests |
| P1 | Partial evaluation/trace | Persistent runs and structured trace | Evaluation regression report |
| P1 | Missing operations | Telemetry, health, backup, deploy, rollback | Production drill reports |
| P2 | CLI/MCP/export viewer | Shared application ports | Contract/integration tests |
| P2 | Optional semantic/vector/agent frameworks | Adopt only by measured trigger | PoC + accepted ADR |
