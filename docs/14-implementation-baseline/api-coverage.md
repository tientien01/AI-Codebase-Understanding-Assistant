# Current API Coverage

Status: Source-verified baseline  
Authority: `backend/app/main.py` and registered route decorators  
Owner: API owner  
Verified: 2026-07-12

## Surface summary

The application currently declares 43 HTTP handlers: one public `/health` handler and 42 handlers under `/api/v1`. Import-session, repository, and settings routers use the optional API-token dependency. When `api_auth_token` is blank, authorization is bypassed; otherwise Bearer or `X-API-Key` must equal the configured token.

| Group | Current handlers | Coverage |
| --- | ---: | --- |
| Health | 1 | Process-level `GET /health`; no dependency readiness split |
| Import sessions | 6 | ZIP/folder/Git create, preview, confirm, cancel |
| Repository management/import compatibility | 5 | list/delete/bulk-delete plus direct ZIP/folder upload |
| Indexing and job inspection/control | 10 | start, status, jobs, pause/resume/cancel, warnings/skipped/failed, staleness |
| Exploration | 4 | overview, reading path, symbols, endpoints |
| Assistant/evidence | 4 | chat, evidence get/validate, ask with selected search evidence |
| Graph/impact | 8 | base and five projection/expansion routes plus impact |
| Search/files | 3 | search, file tree, file content |
| Settings | 2 | safe settings summary and ignore patterns |

## Implemented route families

All paths below are relative to `/api/v1` unless noted.

```text
POST   /import-sessions/upload-zip
POST   /import-sessions/upload-folder
POST   /import-sessions/github
GET    /import-sessions/{id}/preview
POST   /import-sessions/{id}/confirm
DELETE /import-sessions/{id}

GET    /repositories
POST   /repositories/bulk-delete
DELETE /repositories/{repository_id}
POST   /repositories/upload
POST   /repositories/upload-folder
POST   /repositories/{repository_id}/index
GET    /repositories/{repository_id}/index/status
GET    /repositories/{repository_id}/index/jobs
POST   /repositories/{repository_id}/index/jobs/{job_id}/pause|resume|cancel
GET    /repositories/{repository_id}/index/jobs/{job_id}/warnings|skipped-files|failed-files
GET    /repositories/{repository_id}/staleness
GET    /repositories/{repository_id}/overview|reading-path|symbols
GET    /repositories/{repository_id}/api/endpoints
POST   /repositories/{repository_id}/chat
GET    /repositories/{repository_id}/evidence/{evidence_id}
POST   /repositories/{repository_id}/evidence/validate
GET    /repositories/{repository_id}/graph
GET    /repositories/{repository_id}/graph/project-map|dependencies|api-flow|function-flow|data-flow
POST   /repositories/{repository_id}/graph/expand
POST   /repositories/{repository_id}/impact
GET    /repositories/{repository_id}/search
POST   /repositories/{repository_id}/search/ask-with-evidence
GET    /repositories/{repository_id}/files/tree|content

GET    /settings
GET    /settings/ignore-patterns
GET    /health  # unversioned
```

## Production-contract gaps

- No `/health/live` and `/health/ready` split with database/broker/artifact checks.
- No first-class repository index-version, artifact manifest, validation issue, or capability-readiness APIs.
- No durable job attempt/lease/heartbeat/retry/recovery semantics.
- No conversation/message/trace CRUD or persistent evaluation-run API.
- No versioned bounded projection request contract with server-enforced node/edge/coverage budgets.
- No settings mutation/provider test flow on the current frontend production path.
- No cursor pagination for large repository/symbol/search/job collections.
- No idempotency-key contract for import/index/delete operations.
- Optional shared token is not a complete identity, ownership, authorization, or audit design.
- OpenAPI is generated at runtime by FastAPI but is not checked into a verified artifact or drift-tested against frontend types.

## Concentration risk

The 42 versioned handlers are registered from one route module and most response/request types live in one schema module. `FND-003` should split these by domain without changing paths or schemas, capture the current OpenAPI as regression evidence, and keep routes as validation/mapping adapters.
