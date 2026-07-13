# Development Install Report

Status: Local verification passed; GitHub Actions evidence pending

Owner: Project maintainer

Verified: 2026-07-13

Revision: `a394abe518489e044482cc14f51d385b00410bb9` plus the uncommitted `FND-002` working-tree diff

## Scope

This report records the Windows clean-environment verification for `FND-002`: declared runtimes, preserved dependency versions, hashed Python lock installation, npm lock stability, scoped Pytest discovery, frontend gates, and CI workflow structure. It is not immutable CI or release evidence.

## Environment and artifacts

| Item | Verified value |
| --- | --- |
| Python | 3.11.9; supported range `>=3.11,<3.12` |
| uv | 0.11.28 |
| Node.js | 24.14.0; supported range `>=24,<25` |
| npm | 11.9.0; supported range `>=11,<12` |
| Python lock | 109 universal entries; 107 installed on Windows/Python 3.11 |
| Python lock SHA-256 | `74159ECDFC96038CB33BCA2A1F206C9553142C456C97EB83D69CA88597111645` |
| npm lock SHA-256 | `0FFAE560EC5235D70593FC2CC562BCB4F2547E08B8421FB3AE0020C7F969B7AB` |

The Python lock was initially seeded from the existing verified virtualenv so no direct or transitive package changed. A subsequent canonical compile using only `backend/requirements.txt` and the committed output produced the same SHA-256. The lock contains no URL, local path, token, password, or private-index marker.

## Local results

| Gate | Result |
| --- | --- |
| `uv pip sync` into a new Python 3.11 virtualenv | Pass: 107 packages installed from the hashed lock |
| Baseline graph comparison | Pass: all 107 runtime/test packages match the verified existing environment; `uv`, `pip`, and `setuptools` bootstrap tooling excluded |
| `uv pip check` | Pass: all installed packages compatible |
| `python -m pytest tests -q` in the clean environment | Pass: 52 tests, 1 expected duplicate-ZIP warning, 38.95 s |
| Unscoped root `python -m pytest -q` | Pass: the same 52 tests and warning, 43.08 s; no `storage/` test collected |
| Canonical Python lock regeneration | Pass: SHA-256 unchanged on the second canonical generation |
| `npm.cmd ci` | Pass: npm lock SHA-256 unchanged |
| `npm.cmd run test` | Pass: 4 tests across 2 files |
| `npm.cmd run lint` | Pass: zero errors |
| `npm.cmd run build` | Pass: TypeScript and Vite build; 85 modules transformed |
| CI YAML parse | Pass: backend and frontend jobs present |

An earlier intentionally concurrent pair of backend test commands contended for the same test artifact and produced one Windows `PermissionError`; the required commands were then run sequentially, matching CI job order, and both passed. An initial lock attempt was rejected on hash mismatch and was not accepted; regenerating hashes for the preserved versions produced the successful clean install above.

## CI evidence still required

`.github/workflows/ci.yml` pins checkout, setup-uv, and setup-node to full commit SHAs, uses read-only contents permission, installs the exact locks, and runs backend targeted/root tests plus frontend test/lint/build gates. The workflow has not run on GitHub because this working tree is not committed or pushed. `FND-002` remains `in_progress` until an immutable successful workflow run is linked here.
