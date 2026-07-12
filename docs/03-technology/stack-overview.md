# Approved Stack and Adoption Boundaries

## Application stack

| Concern | Choice | Why | Status |
| --- | --- | --- | --- |
| Backend language/API | Python + FastAPI | Reuses analysis code; typed OpenAPI and async I/O | Accepted |
| Validation/config | Pydantic/Pydantic Settings | Existing typed boundaries | Accepted |
| ORM/transactions | SQLAlchemy 2.x style | Mature PostgreSQL/SQLite support | Accepted direction |
| Migrations | Alembic | Versioned production schema | Accepted |
| Frontend | React + TypeScript + Vite | Existing SPA fits graph/workspace UX | Accepted |
| Routing | React Router | Deep links and browser navigation | Accepted |
| Server state | TanStack Query | Cache, retry, cancellation, invalidation | Accepted |
| Graph canvas/layout | XYFlow + Dagre | Common interactive directed graph baseline | Proposed; benchmark before install |
| Backend tests | Pytest | Existing suite | Accepted |
| Frontend/E2E | Vitest + Testing Library + MSW + Playwright | Layered behavior/contract/E2E coverage | Accepted direction |

## Infrastructure stack

| Concern | Choice | Boundary |
| --- | --- | --- |
| Local/test database | SQLite | Not the public production persistence profile |
| Production database | PostgreSQL | Authoritative relational state |
| Job broker | Redis | Delivery/coordination only |
| Queue library | RQ or Dramatiq | Must be selected by recovery/cancellation PoC and ADR |
| Artifacts | Filesystem local; S3-compatible production | Access through `ArtifactStore` port |
| Vector retrieval | Existing deterministic baseline | pgvector only after quality/scale benchmark |
| Telemetry | Structured logging + OpenTelemetry + Prometheus-compatible metrics | Export backend is deployment-configurable |
| Packaging/deploy | Locked Python/Node dependencies, Docker, Compose, TLS proxy | Kubernetes deferred |

## Dependency introduction checklist

An accepted task must document exact package/purpose, license and maintenance, supported version range, configuration, transitive/security impact, migration, failure behavior, observability, tests, deployment, lockfile, and rollback/removal.

## Prohibited implicit choices

No code may silently introduce a second ORM, HTTP framework, global frontend state system, graph database, vector database, full-text service, agent framework, queue, or styling system. Such changes require a measured trigger and accepted ADR.
