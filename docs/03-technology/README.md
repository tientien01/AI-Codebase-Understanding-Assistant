# Technology Architecture

Technology is adopted through requirement → assessment → PoC → ADR → plan → task → evidence. Listing a candidate does not authorize installation.

## Production v1 target

| Layer | Accepted direction |
| --- | --- |
| Frontend | React, TypeScript, Vite, React Router, TanStack Query |
| Graph UI | XYFlow/React Flow + Dagre initially; benchmark before ELK/Graphology |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | SQLite for local/test; PostgreSQL for production |
| Migration | Alembic |
| Jobs | Redis broker plus one queue implementation selected by ADR/PoC |
| Storage | Filesystem adapter for local and initial single-node production with backup/checksum/atomic-write evidence; S3-compatible adapter optional |
| Retrieval | Deterministic hybrid baseline; pgvector only after benchmark |
| Testing | Pytest, Vitest, Testing Library, MSW, Playwright |
| Observability | Structured logging, OpenTelemetry, Prometheus-compatible metrics |
| Deployment | Docker images, Docker Compose production profile, reverse proxy/TLS |

## Rules

- Pin tested ranges and commit lockfiles; never depend on `latest`.
- PostgreSQL is authoritative; Redis is coordination only.
- Do not add Kubernetes, Kafka, graph DB, external vector DB, OpenSearch, LangGraph, Redux, or Monaco without a measured trigger and accepted ADR.
- Every external service requires configuration, health, timeout, metrics, backup/retention where applicable, and rollback documentation.

## Detailed configuration

`environment-and-configuration.md` contains the configuration groups, variables, provider/test settings, indexing controls, and capability defaults. Interpret it through `stack-profiles.md`: local-compatible defaults do not automatically qualify as production defaults.
