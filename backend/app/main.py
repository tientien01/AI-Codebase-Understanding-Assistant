from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.assistant import router as assistant_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.exploration import router as exploration_router
from app.api.v1.routes.graph import router as graph_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.import_sessions import router as import_sessions_router
from app.api.v1.routes.indexing import router as indexing_router
from app.api.v1.routes.repositories import router as repositories_router
from app.api.v1.routes.search import router as search_router
from app.api.v1.routes.settings import router as settings_router
from app.core.config import settings
from app.core.errors import DomainError, domain_error_handler
from app.api.dependencies import application_container


app = FastAPI(title="AI Codebase Assistant", version="0.1.0")
app.state.access_service = application_container.access_service

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(DomainError, domain_error_handler)
app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(import_sessions_router, prefix=settings.api_v1_prefix)
app.include_router(repositories_router, prefix=settings.api_v1_prefix)
app.include_router(indexing_router, prefix=settings.api_v1_prefix)
app.include_router(exploration_router, prefix=settings.api_v1_prefix)
app.include_router(assistant_router, prefix=settings.api_v1_prefix)
app.include_router(graph_router, prefix=settings.api_v1_prefix)
app.include_router(search_router, prefix=settings.api_v1_prefix)
app.include_router(settings_router, prefix=settings.api_v1_prefix)
