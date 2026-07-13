"""CLI for the explicitly managed legacy SQLite upgrade path."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine

from app.db.legacy_upgrade import migrate_supported_legacy_sqlite


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate the supported legacy SQLite database")
    parser.add_argument("source_database", type=Path)
    parser.add_argument("managed_source_root", type=Path)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL is required")
    engine = create_engine(database_url)
    try:
        counts = migrate_supported_legacy_sqlite(args.source_database, engine, args.managed_source_root)
    finally:
        engine.dispose()
    print("Migration completed: " + ", ".join(f"{name}={count}" for name, count in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
