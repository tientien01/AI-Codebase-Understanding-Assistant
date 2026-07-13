# Queue Selection PoC Report

Status: Verified JOB-002 evidence

Verified: 2026-07-13

Environment: Docker Desktop; Python 3.11.13; Redis 8.2.7 disposable broker; RQ 2.10.0; Dramatiq 2.2.0; three runs per scenario; 30-second scenario timeout

## Method

`poc/queue/benchmark.py` sends only an opaque job ID. A separate SQLite database simulates application-owned durable state and cancellation intent. Each candidate receives the same five scenarios. Forced worker loss recursively kills the worker and its execution descendants before a replacement starts.

The committed `poc/queue/results.json` is the machine-readable result. Dependency resolution is hashed in `poc/queue/requirements-lock.txt`.

## Results

| Candidate | Scenario | Passed | Total elapsed ms (min/median/max) |
| --- | --- | ---: | ---: |
| RQ 2.10.0 | JSON job-ID payload | 3/3 | 6 / 6 / 35 |
| RQ 2.10.0 | Forced worker-loss recovery | 0/3 | 30,254 / 30,266 / 30,293 |
| RQ 2.10.0 | Queued cancellation | 3/3 | 195 / 198 / 315 |
| RQ 2.10.0 | Running cancellation | 3/3 | 274 / 274 / 284 |
| RQ 2.10.0 | Broker outage | 3/3 | 37 / 44 / 45 |
| Dramatiq 2.2.0 | JSON job-ID payload | 3/3 | 5 / 6 / 17 |
| Dramatiq 2.2.0 | Forced worker-loss recovery | 3/3 | 3,181 / 3,405 / 3,894 |
| Dramatiq 2.2.0 | Queued cancellation | 3/3 | 193 / 195 / 205 |
| Dramatiq 2.2.0 | Running cancellation | 3/3 | 278 / 281 / 288 |
| Dramatiq 2.2.0 | Broker outage | 3/3 | 19 / 22 / 37 |

RQ's interrupted row stayed `running` with one attempt for the entire timeout in all runs. Dramatiq redelivered to the replacement worker and completed the same logical ID on attempt two in all runs. Cooperative cancellation was observed by the workload in 69–85 ms across both candidates; table timings include worker startup and teardown.

## Decision

Dramatiq passed 15/15 correctness runs and is selected by `ADR-0003`. RQ failed the mandatory recovery scenario in 3/3 runs and is rejected for the first production adapter. This is a correctness selection, not a throughput benchmark.

## Reproduction

```powershell
docker compose -f poc/queue/compose.yml build
docker compose -f poc/queue/compose.yml run --rm benchmark
backend\.venv\Scripts\python.exe -m json.tool poc/queue/results.json
git diff --check
docker compose -f poc/queue/compose.yml down -v
```

## Limits and follow-up

- The two-second Dramatiq Redis heartbeat timeout accelerates the PoC; production timing requires JOB-004 resilience evidence.
- SQLite represents only the separation of application state from broker state. JOB-003/004 must exercise the real PostgreSQL lease and fencing model.
- No backend dependency, adapter, worker, deployment configuration, or application behavior changed in JOB-002.
