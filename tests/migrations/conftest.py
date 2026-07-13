from __future__ import annotations

import os
from pathlib import Path
import sys
from uuid import uuid4

from alembic import command
from alembic.config import Config
import psycopg
from psycopg import sql
import pytest
from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _admin_url() -> str:
    value = os.environ.get("TEST_POSTGRES_ADMIN_URL")
    if not value:
        pytest.skip("TEST_POSTGRES_ADMIN_URL is required for PostgreSQL migration tests")
    return value


@pytest.fixture
def production_database():
    admin_url = _admin_url()
    database_name = f"aica_test_{uuid4().hex}"
    psycopg_url = admin_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(psycopg_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    database_url = admin_url.rsplit("/", 1)[0] + f"/{database_name}"
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    engine = create_engine(database_url)
    try:
        command.upgrade(config, "head")
        yield config, engine
    finally:
        engine.dispose()
        with psycopg.connect(psycopg_url, autocommit=True) as connection:
            if not database_name.startswith("aica_test_"):
                raise RuntimeError("Refusing to drop an unmanaged database")
            connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name)))
