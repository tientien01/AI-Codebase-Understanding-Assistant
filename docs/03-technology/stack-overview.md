# Approved Stack and Adoption Boundaries

## Application stack

| Concern | Choice | Why | Status |
| --- | --- | --- | --- |
| Backend language/API | Python + FastAPI | Reuses analysis code; typed OpenAPI and async I/O | Accepted |
| Validation/config | Pydantic/Pydantic Settings | Existing typed boundaries | Accepted |
| ORM/transactions | SQLAlchemy 2.x style | Mature PostgreSQL/SQLite support | Accepted direction |
| Migrations | Alembic | Versioned production schema | Accepted |
| PostgreSQL driver | Psycopg 3 binary | SQLAlchemy/Alembic PostgreSQL 18 migration and integration profile | Implemented by `DAT-002` |
| Frontend | React + TypeScript + Vite | Existing SPA fits graph/workspace UX | Accepted |
| Routing | React Router | Deep links and browser navigation | Accepted |
| Server state | TanStack Query | Cache, retry, cancellation, invalidation | Accepted |
| Graph canvas/layout | XYFlow + Dagre | Common interactive directed graph baseline | Proposed; benchmark before install |
| Backend tests | Pytest | Existing suite | Accepted |
| Frontend/E2E | Vitest + Testing Library + MSW + Playwright | Layered behavior/contract/E2E coverage | Accepted direction |
| Development lock tooling | `uv==0.11.28` | Universal hashed Python 3.11 requirements lock and exact environment sync | Accepted by `ADR-0002` |
| Production job queue | Dramatiq `2.2.0` | Redis-backed at-least-once ID delivery; PostgreSQL owns lifecycle, lease, retry, and cancellation | Accepted by `ADR-0003`; integration deferred to `JOB-003` |

## Infrastructure stack

| Concern | Choice | Boundary |
| --- | --- | --- |
| Local application database | SQLite | Default developer runtime; no Docker requirement |
| Production/integration database | PostgreSQL 18 | Authoritative relational state; disposable integration profile is pinned to 18.4 |
| Job broker | Redis | Delivery/coordination only |
| Queue library | Dramatiq 2.2.0 | Selected by the JOB-002 recovery/cancellation PoC and `ADR-0003` |
| Artifacts | Filesystem local; S3-compatible production | Access through `ArtifactStore` port |
| Vector retrieval | Existing deterministic baseline | pgvector only after quality/scale benchmark |
| Telemetry | Structured logging + OpenTelemetry + Prometheus-compatible metrics | Export backend is deployment-configurable |
| Packaging/deploy | Locked Python/Node dependencies, Docker, Compose, TLS proxy | Kubernetes deferred |

The first reproducible development and CI profile supports Python `>=3.11,<3.12`, Node.js `>=24,<25`, and npm `>=11,<12`. Runtime-major changes require compatibility review and refreshed install evidence.

## Dependency introduction checklist

An accepted task must document exact package/purpose, license and maintenance, supported version range, configuration, transitive/security impact, migration, failure behavior, observability, tests, deployment, lockfile, and rollback/removal.

## Prohibited implicit choices

No code may silently introduce a second ORM, HTTP framework, global frontend state system, graph database, vector database, full-text service, agent framework, queue, or styling system. Such changes require a measured trigger and accepted ADR.
