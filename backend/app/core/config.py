from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "ai-codebase-assistant"
    api_v1_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'storage/app.db'}"
    repository_storage_dir: Path = PROJECT_ROOT / "storage/repositories"
    upload_storage_dir: Path = PROJECT_ROOT / "storage/uploads"
    max_upload_size_mb: int = 200
    max_file_size_mb: int = 1
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    llm_provider: str = "fake"
    llm_model: str = "fake-chat-model"
    llm_api_key: str = ""
    embedding_provider: str = "fake"
    embedding_model: str = "fake-embedding-model"
    embedding_api_key: str = ""
    vector_store_provider: str = "local"
    enable_agent_trace: bool = True
    vite_api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8")


settings = Settings()


def _resolve_project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _resolve_sqlite_url(database_url: str) -> str:
    sqlite_prefix = "sqlite:///"
    if not database_url.startswith(sqlite_prefix):
        return database_url
    raw_path = database_url.removeprefix(sqlite_prefix)
    database_path = Path(raw_path)
    if database_path.is_absolute():
        return database_url
    return f"{sqlite_prefix}{(PROJECT_ROOT / database_path).as_posix()}"


settings.repository_storage_dir = _resolve_project_path(settings.repository_storage_dir)
settings.upload_storage_dir = _resolve_project_path(settings.upload_storage_dir)
settings.database_url = _resolve_sqlite_url(settings.database_url)
