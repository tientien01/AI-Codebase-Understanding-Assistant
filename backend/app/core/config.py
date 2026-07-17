from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_ENV_FILE = None if os.environ.get("APP_ENV") == "test" else BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    app_env: Literal["test", "local", "production"] = "local"
    app_name: str = "ai-codebase-assistant"
    api_v1_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'storage/app.db'}"
    redis_url: str = ""
    index_lease_seconds: int = 60
    index_heartbeat_seconds: int = 15
    index_max_attempts: int = 3
    artifact_root: Path = PROJECT_ROOT / "storage/artifacts"
    repository_storage_dir: Path = PROJECT_ROOT / "storage/repositories"
    upload_storage_dir: Path = PROJECT_ROOT / "storage/uploads"
    max_upload_size_mb: int = 2048
    upload_chunk_size_mb: int = 4
    max_file_size_mb: int = 1
    max_zip_entries: int = 200_000
    max_extracted_size_mb: int = 4096
    max_archive_compression_ratio: int = 100
    max_path_depth: int = 30
    git_clone_timeout_seconds: int = 120
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    llm_provider: str = "fake"
    llm_model: str = "fake-chat-model"
    llm_api_key: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_timeout_seconds: float = 30.0
    embedding_provider: str = "fake"
    embedding_model: str = "fake-embedding-model"
    embedding_api_key: str = ""
    vector_store_provider: str = "local"
    enable_agent_trace: bool = True
    enable_cfg_dfg: bool = True
    api_auth_token: str = ""
    operator_bootstrap_credential: SecretStr = SecretStr("")
    session_absolute_seconds: int = 43_200
    session_idle_seconds: int = 1_800
    api_token_max_seconds: int = 7_776_000
    audit_retention_seconds: int = 31_536_000
    vite_api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=SETTINGS_ENV_FILE, env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_database_profile(self) -> "Settings":
        if self.app_env == "production" and not self.database_url.startswith(
            ("postgresql://", "postgresql+psycopg://")
        ):
            raise ValueError("Production profile requires a PostgreSQL DATABASE_URL")
        if self.app_env == "production" and not self.redis_url.startswith(
            ("redis://", "rediss://")
        ):
            raise ValueError("Production profile requires a Redis REDIS_URL")
        if min(
            self.index_lease_seconds,
            self.index_heartbeat_seconds,
            self.index_max_attempts,
        ) <= 0:
            raise ValueError("Index lease, heartbeat, and attempt settings must be positive")
        if self.index_heartbeat_seconds >= self.index_lease_seconds:
            raise ValueError("INDEX_HEARTBEAT_SECONDS must be shorter than INDEX_LEASE_SECONDS")
        if min(
            self.max_upload_size_mb,
            self.upload_chunk_size_mb,
            self.max_file_size_mb,
            self.max_zip_entries,
            self.max_extracted_size_mb,
            self.max_archive_compression_ratio,
            self.max_path_depth,
            self.git_clone_timeout_seconds,
        ) <= 0:
            raise ValueError("Import quotas and Git clone timeout must be positive")
        required_job_settings = {
            "index_lease_seconds",
            "index_heartbeat_seconds",
            "index_max_attempts",
        }
        if self.app_env == "production" and not required_job_settings.issubset(
            self.model_fields_set
        ):
            raise ValueError(
                "Production profile requires explicit index lease, heartbeat, and attempt settings"
            )
        if self.app_env == "production" and "artifact_root" not in self.model_fields_set:
            raise ValueError("Production profile requires an explicit ARTIFACT_ROOT")
        if min(
            self.session_absolute_seconds,
            self.session_idle_seconds,
            self.api_token_max_seconds,
            self.audit_retention_seconds,
        ) <= 0:
            raise ValueError("Operator access and audit lifetimes must be positive")
        if self.session_idle_seconds > self.session_absolute_seconds:
            raise ValueError("SESSION_IDLE_SECONDS cannot exceed SESSION_ABSOLUTE_SECONDS")
        if not 0 < self.ollama_timeout_seconds <= 120:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than zero and at most 120")
        if self.app_env == "production" and self.api_auth_token.strip():
            raise ValueError("Production profile forbids the shared API_AUTH_TOKEN")
        required_access_settings = {
            "operator_bootstrap_credential",
            "session_absolute_seconds",
            "session_idle_seconds",
            "api_token_max_seconds",
            "audit_retention_seconds",
        }
        if self.app_env == "production" and not required_access_settings.issubset(self.model_fields_set):
            raise ValueError("Production profile requires explicit operator access settings")
        if self.app_env == "production" and not self.operator_bootstrap_credential.get_secret_value():
            raise ValueError("Production profile requires an operator bootstrap credential")
        return self


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


settings.artifact_root = _resolve_project_path(settings.artifact_root)
settings.repository_storage_dir = _resolve_project_path(settings.repository_storage_dir)
settings.upload_storage_dir = _resolve_project_path(settings.upload_storage_dir)
settings.database_url = _resolve_sqlite_url(settings.database_url)
