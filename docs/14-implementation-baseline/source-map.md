# Current Source Map

| Domain | Source |
| --- | --- |
| API | `backend/app/api/v1/routes/` |
| Schemas | `backend/app/schemas/api.py` |
| Ingestion | `backend/app/services/ingestion/` |
| Indexing | `backend/app/services/indexing/` |
| Parsing | `backend/app/services/parsing/` |
| Deep code analysis | `backend/app/services/code_analysis/` |
| Graph/projections | `backend/app/services/graph/` |
| Retrieval | `backend/app/services/retrieval/` |
| Evidence | `backend/app/services/evidence/` |
| Assistant | `backend/app/services/chat/` |
| Impact | `backend/app/services/impact/` |
| Persistence | `backend/app/db/`, `services/repositories/repository_store.py` |
| Frontend API/state | `frontend/src/api/`, `frontend/src/hooks/` |
| Frontend surfaces | `frontend/src/pages/`, `frontend/src/components/` |
| Tests/fixture | `tests/` |

Agents use this map for targeted inspection and must not scan ignored dependency/build/runtime storage directories.
