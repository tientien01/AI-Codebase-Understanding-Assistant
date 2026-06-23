from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.repositories import router as repositories_router
from app.core.config import settings
from app.core.errors import DomainError, domain_error_handler


app = FastAPI(title="AI Codebase Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(DomainError, domain_error_handler)
app.include_router(health_router)
app.include_router(repositories_router, prefix=settings.api_v1_prefix)
