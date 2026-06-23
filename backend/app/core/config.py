from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "ai-codebase-assistant"
    api_v1_prefix: str = "/api/v1"
    repository_storage_dir: Path = PROJECT_ROOT / "storage/repositories"
    upload_storage_dir: Path = PROJECT_ROOT / "storage/uploads"
    index_storage_dir: Path = PROJECT_ROOT / "storage/indexes"
    max_file_size_mb: int = 1
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=None)


settings = Settings()
