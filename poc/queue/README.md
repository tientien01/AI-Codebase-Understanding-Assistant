# Queue selection PoC

This disposable harness compares RQ 2.10.0 and Dramatiq 2.2.0 against the same Redis-backed delivery scenarios. SQLite represents application-owned durable state so cancellation intent is not stored in broker metadata.

Run from the repository root:

```powershell
docker compose -f poc/queue/compose.yml build
docker compose -f poc/queue/compose.yml run --rm benchmark
backend\.venv\Scripts\python.exe -m json.tool poc/queue/results.json
docker compose -f poc/queue/compose.yml down -v
```

The harness runs five scenarios three times per candidate and overwrites `results.json`. A candidate passes selection only when every scenario passes in all three runs. Redis and the benchmark state database are disposable; no application database or backend dependency is used.
