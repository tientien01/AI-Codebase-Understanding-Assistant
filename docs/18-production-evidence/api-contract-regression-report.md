# API Contract Regression Report

Status: Verified

Owner: Project maintainer

Verified: 2026-07-13

## Scope

This report records `FND-003` evidence for splitting current FastAPI route and Pydantic schema ownership without changing the verified MVP HTTP contract. It does not claim that unimplemented production-target endpoints or semantics are complete.

## Artifact boundary

The OpenAPI document was exported before moving any handler or model and committed as `docs/06-api-and-integrations/artifacts/openapi-v1.json`.

| Item | Verified value |
| --- | --- |
| Artifact size | 151,552 bytes |
| Pre-split SHA-256 | `00FCA7CF351DC7C21AD0CE6B7690D87155DA830055DBA1C69CF79FF7EAF2F031` |
| Post-split SHA-256 | `00FCA7CF351DC7C21AD0CE6B7690D87155DA830055DBA1C69CF79FF7EAF2F031` |
| HTTP operations | 43 total: 1 health and 42 under `/api/v1` |
| Schema compatibility exports | 63 Pydantic models |
| Domain ownership | 8 route modules and 8 schema modules |

The deterministic exporter writes only with `--write`. Its `--check` mode compares generated content to the committed artifact and exits non-zero on missing or changed content.

## Verification results

| Gate | Result |
| --- | --- |
| `backend/.venv/Scripts/python.exe backend/scripts/export_openapi.py --check` | Pass: artifact up to date; no rewrite |
| `backend/.venv/Scripts/python.exe -m pytest tests/test_api_contract.py -q` | Pass: 5 tests |
| `backend/.venv/Scripts/python.exe -m pytest tests -q` | Pass: 57 tests in 34.46 s; 1 existing duplicate-ZIP warning |
| Route ownership | Pass: module counts `4, 4, 8, 6, 10, 5, 3, 2`; all endpoints owned by their declared module |
| Schema ownership | Pass: all compatibility exports resolve to one of eight domain schema modules |
| Auth boundary | Pass: all 42 versioned routes retain `require_api_auth` |
| Operation IDs | Pass: all 43 are present and unique |

No dependency, service, database, model, frontend, fixture, or runtime-storage file was changed. The broad application facade remains intentionally unchanged for `FND-004`.
