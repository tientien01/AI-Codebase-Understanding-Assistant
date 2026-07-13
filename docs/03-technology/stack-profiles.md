# Stack Profiles

## Test

Python `>=3.11,<3.12`, Node `>=24,<25`, npm `>=11,<12`, hashed Python requirements lock, npm lock, temporary SQLite, fake LLM/embedding, fake queue, temporary artifacts, deterministic fixtures.

## Local

The same locked Python/Node toolchain as Test, FastAPI, Vite, SQLite, filesystem artifacts, deterministic providers; optional Redis worker for production-like debugging.

## Production-like

Containerized Web/API/Worker, PostgreSQL, Redis, local S3-compatible emulator if needed, telemetry collector.

## Production

Web/API/Worker containers, managed or backed-up PostgreSQL, Redis broker, durable artifact storage, TLS reverse proxy, monitoring, alerts, backup and restore.

Configuration is validated at startup. Missing production secrets, origins, storage, database, queue, or signing configuration must fail fast.
