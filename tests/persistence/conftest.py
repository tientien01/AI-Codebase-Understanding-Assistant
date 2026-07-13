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


@pytest.fixture
def production_database():
    admin_url = os.environ.get("TEST_POSTGRES_ADMIN_URL")
    if not admin_url:
        pytest.skip("TEST_POSTGRES_ADMIN_URL is required")
    name = f"aica_test_{uuid4().hex}"
    driver_url = admin_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(driver_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = admin_url.rsplit("/", 1)[0] + f"/{name}"
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    engine = create_engine(url)
    try:
        command.upgrade(config, "head")
        yield config, engine, url
    finally:
        engine.dispose()
        with psycopg.connect(driver_url, autocommit=True) as connection:
            if not name.startswith("aica_test_"):
                raise RuntimeError("Refusing to drop an unmanaged database")
            connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
