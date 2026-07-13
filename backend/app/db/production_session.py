"""Fail-fast PostgreSQL engine/session boundary for the production profile."""

from __future__ import annotations

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import BACKEND_ROOT, settings


class ProductionDatabaseError(RuntimeError):
    """Stable startup failure that never includes the raw database URL."""


def expected_alembic_head() -> str:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    return ScriptDirectory.from_config(config).get_current_head()


def verify_production_database(engine: Engine) -> None:
    """Require connectivity and the exact repository Alembic head."""

    try:
        with engine.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception as exc:
        raise ProductionDatabaseError("Production database is unavailable or not migrated") from exc
    if revision != expected_alembic_head():
        raise ProductionDatabaseError("Production database revision does not match Alembic head")


def create_production_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    if not url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise ProductionDatabaseError("Production database profile requires PostgreSQL")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        verify_production_database(engine)
    except Exception:
        engine.dispose()
        raise
    return engine


def create_production_session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
