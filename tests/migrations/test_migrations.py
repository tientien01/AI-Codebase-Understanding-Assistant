from __future__ import annotations

from pathlib import Path

from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
import pytest

from app.db.legacy_upgrade import LegacyUpgradeError, migrate_supported_legacy_sqlite
from app.db.production_base import ProductionBase
import app.db.production_models  # noqa: F401
from tests.migrations.legacy_fixture import build_supported_legacy_fixture


EXPECTED_TABLES = set(ProductionBase.metadata.tables)


def test_production_metadata_matches_dat_001_table_inventory() -> None:
    assert len(EXPECTED_TABLES) == 35


def test_fresh_upgrade_has_expected_tables_revision_indexes_and_triggers(production_database) -> None:
    _, engine = production_database
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == EXPECTED_TABLES | {"alembic_version"}
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0002_operator_authentication"
        principal_columns = {column["name"] for column in inspect(engine).get_columns("operator_principals")}
        assert "password_hash" in principal_columns
        indexes = set(connection.scalars(text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")))
        assert {"ix_files_path", "ix_graph_edges_forward", "uq_index_jobs_one_active"} <= indexes
        triggers = set(connection.scalars(text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")))
        assert {"trg_repositories_active_version", "trg_index_versions_active_lifecycle", "trg_audit_events_append_only"} <= triggers


def test_schema_has_zero_alembic_drift(production_database) -> None:
    config, _ = production_database
    command.check(config)


def test_id_prefix_and_append_only_audit_constraints(production_database) -> None:
    _, engine = production_database
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO operator_principals (id, display_name) VALUES ('bad', 'Bad')"))
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO operator_principals (id, display_name) VALUES ('principal_test', 'Test')"))
        connection.execute(text("INSERT INTO audit_events (id, principal_id, event_type, outcome) VALUES ('audit_test', 'principal_test', 'test', 'ok')"))
    with pytest.raises(DBAPIError, match="append-only"):
        with engine.begin() as connection:
            connection.execute(text("UPDATE audit_events SET outcome = 'changed' WHERE id = 'audit_test'"))


def test_empty_downgrade_and_forward_recovery(production_database) -> None:
    config, engine = production_database
    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES | {"alembic_version"}


def test_0001_operator_upgrade_preserves_uninitialized_principal(production_database) -> None:
    config, engine = production_database
    command.downgrade(config, "0001_production_baseline")
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO operator_principals (id, display_name) VALUES ('principal_existing', 'Existing')")
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, display_name, password_hash FROM operator_principals")
        ).mappings().one()
    assert row == {
        "id": "principal_existing",
        "display_name": "Existing",
        "password_hash": None,
    }


def test_supported_legacy_upgrade_is_atomic(production_database, tmp_path: Path) -> None:
    _, engine = production_database
    source, managed_root = build_supported_legacy_fixture(tmp_path)
    counts = migrate_supported_legacy_sqlite(source, engine, managed_root)
    assert counts["repositories"] == 1
    assert counts["files"] == counts["symbols"] == counts["endpoints"] == counts["chunks"] == 1
    assert counts["graph_nodes"] == 2
    assert counts["graph_edges"] == counts["evidence"] == counts["index_jobs"] == 1


def test_external_legacy_source_is_rejected_without_target_rows(production_database, tmp_path: Path) -> None:
    _, engine = production_database
    source, managed_root = build_supported_legacy_fixture(tmp_path)
    with __import__("sqlite3").connect(source) as connection:
        connection.execute("UPDATE repositories SET source_path = ?", (str(tmp_path),))
    with pytest.raises(LegacyUpgradeError, match="outside the managed source root"):
        migrate_supported_legacy_sqlite(source, engine, managed_root)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM repositories")) == 0
