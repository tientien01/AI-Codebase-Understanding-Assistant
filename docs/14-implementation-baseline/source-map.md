# Current Source Map

| Domain | Source |
| --- | --- |
| API | `backend/app/api/v1/routes/` |
| API dependency providers | `backend/app/api/dependencies.py` |
| Schemas | `backend/app/schemas/api.py` |
| Application composition/use cases | `backend/app/services/application/` |
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
| Production PostgreSQL metadata | `backend/app/db/production_base.py`, `backend/app/db/production_models/` |
| Alembic migrations | `backend/migrations/`, configured by `backend/alembic.ini` |
| Supported legacy upgrade | `backend/app/db/legacy_upgrade.py`, `backend/scripts/migrate_legacy_sqlite.py` |
| Production DB session/profile | `backend/app/db/production_session.py`, `backend/app/core/config.py` |
| Repository persistence port/adapters | `backend/app/services/repositories/repository_port.py`, `repository_store.py`, `production_repository_store.py` |
| Persisted job/version/artifact commands | `backend/app/services/indexing/job_state_store.py` |
| Job queue/delivery boundary | `backend/app/services/indexing/job_queue.py`, `job_delivery_service.py` |
| Dedicated indexing worker | `backend/app/workers/indexing_worker.py` |
| Frontend API/state | `frontend/src/api/`, `frontend/src/hooks/` |
| Frontend surfaces | `frontend/src/pages/`, `frontend/src/components/` |
| Tests/fixture | `tests/` |

The versioned API routes resolve domain-specific application boundaries from one
single-process composition root. `backend/app/services/codebase_service.py` remains
a compatibility adapter for direct callers; versioned routes no longer import it.

Agents use this map for targeted inspection and must not scan ignored dependency/build/runtime storage directories.
