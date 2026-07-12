# Stack Profiles

## Test

Temporary SQLite, fake LLM/embedding, fake queue, temporary artifacts, deterministic fixtures.

## Local

FastAPI, Vite, SQLite, filesystem artifacts, deterministic providers; optional Redis worker for production-like debugging.

## Production-like

Containerized Web/API/Worker, PostgreSQL, Redis, local S3-compatible emulator if needed, telemetry collector.

## Production

Web/API/Worker containers, managed or backed-up PostgreSQL, Redis broker, durable artifact storage, TLS reverse proxy, monitoring, alerts, backup and restore.

Configuration is validated at startup. Missing production secrets, origins, storage, database, queue, or signing configuration must fail fast.
