# ADR-0001: Production Foundations

Status: Accepted

## Decision

Keep Python/FastAPI and React/TypeScript/Vite. Use PostgreSQL with Alembic for production persistence, a durable Redis-backed worker selected by PoC, immutable artifact versions, and Docker Compose as the initial self-hosted production topology.

Static parsing/resolution/graph validation is authoritative. LLM and embedding providers are replaceable optional enrichers. The agent is a bounded orchestrator over typed tools and validated evidence.

Production v1 has one local operator principal. Browser authentication uses a server-side secure session cookie with CSRF/origin protection; CLI/MCP uses individually revocable hashed operator API tokens. A blank/shared development token is not a production access model. Multi-user sharing and RBAC remain deferred.

## Consequences

The current SQLite/thread MVP remains a local profile while migration tasks replace its production path. Kubernetes, microservices, graph DB, external vector DB, OpenSearch, and LangGraph are deferred until measured requirements justify them.
