from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


settings.repository_storage_dir.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    columns_by_table = {
        "repositories": {
            "source_label": "TEXT",
            "current_index_version": "INTEGER DEFAULT 0",
        },
        "indexing_jobs": {
            "index_version": "INTEGER DEFAULT 0",
            "skipped_files_json": "TEXT DEFAULT '[]'",
            "failed_files_json": "TEXT DEFAULT '[]'",
        },
        "file_records": {"index_version": "INTEGER DEFAULT 0"},
        "symbol_records": {"index_version": "INTEGER DEFAULT 0"},
        "endpoint_records": {"index_version": "INTEGER DEFAULT 0"},
        "chunk_records": {"index_version": "INTEGER DEFAULT 0"},
        "graph_nodes": {"index_version": "INTEGER DEFAULT 0"},
        "graph_edges": {"index_version": "INTEGER DEFAULT 0"},
        "evidence": {
            "index_version": "INTEGER DEFAULT 0",
            "is_stale": "INTEGER DEFAULT 0",
        },
    }

    with engine.begin() as connection:
        for table_name, required_columns in columns_by_table.items():
            existing = {
                row[1]
                for row in connection.execute(text(f"PRAGMA table_info({table_name})"))
            }
            for column_name, column_type in required_columns.items():
                if column_name not in existing:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
