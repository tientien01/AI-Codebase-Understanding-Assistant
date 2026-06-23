from fastapi import FastAPI

from app.api.auth.routes import router as auth_router

app = FastAPI(title="Fixture App")
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
