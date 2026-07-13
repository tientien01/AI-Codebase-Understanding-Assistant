from __future__ import annotations

import hashlib
from pathlib import Path

from alembic import command
from pydantic import ValidationError
import pytest
from sqlalchemy import select

from app.core.config import Settings, settings
from app.db.production_base import ProductionBase
from app.db.production_session import ProductionDatabaseError, create_production_engine
from app.schemas.api import EvidenceDTO, GraphEdgeDTO, GraphNodeDTO
from app.services.index_models import ChunkRecord, EndpointRecord, FileRecord, IndexingJobRecord, RepositoryState, SymbolRecord
from app.services.repositories.production_repository_store import ProductionRepositoryError, ProductionRepositoryStore


def _repository(root: Path, *, dangling: bool = False) -> RepositoryState:
    source = root / "repo_test" / "source"
    source.mkdir(parents=True, exist_ok=True)
    content = "def hello():\n    return 'hello'\n"
    source_file = source / "app.py"
    source_file.write_text(content, encoding="utf-8")
    digest = hashlib.sha256(content.encode()).hexdigest()
    return RepositoryState(
        id="repo_test", name="Test", source_type="upload_folder", source_uri=None, source_path=source,
        source_label="fixture", status="indexed", current_index_version=1, project_fingerprint=digest,
        files=[FileRecord(path="app.py", absolute_path=source_file, language="python", file_type="source", size_bytes=len(content), content_hash=digest)],
        symbols=[SymbolRecord(id="symbol:v1:hello", name="hello", symbol_type="function", file_path="app.py", start_line=1, end_line=2)],
        endpoints=[EndpointRecord(method="GET", path="/hello", handler="hello", file_path="app.py", start_line=1, end_line=2)],
        chunks=[ChunkRecord(id="chunk:v1:hello", file_path="app.py", chunk_type="symbol", content=content, start_line=1, end_line=2, symbol_name="hello", content_hash=digest)],
        graph_nodes=[
            GraphNodeDTO(id="node_a", type="function", label="hello", file_path="app.py", start_line=1, end_line=2),
            GraphNodeDTO(id="node_b", type="module", label="app", file_path="app.py", start_line=1, end_line=2),
        ],
        graph_edges=[GraphEdgeDTO(source="node_a", target="missing" if dangling else "node_b", type="DEFINED_IN", confidence=1.0)],
        current_step="completed",
    )


def test_production_profile_requires_postgresql() -> None:
    with pytest.raises(ValidationError, match="requires a PostgreSQL"):
        Settings(_env_file=None, app_env="production", database_url="sqlite:///local.db")


def test_production_profile_requires_redis() -> None:
    with pytest.raises(ValidationError, match="requires a Redis"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+psycopg://localhost/app",
        )


def test_local_profile_does_not_require_redis() -> None:
    configured = Settings(_env_file=None, app_env="local", redis_url="")
    assert configured.redis_url == ""


def test_production_engine_requires_alembic_head(production_database) -> None:
    config, engine, url = production_database
    command.downgrade(config, "base")
    engine.dispose()
    with pytest.raises(ProductionDatabaseError, match="revision does not match"):
        create_production_engine(url)


def test_composition_root_selects_store_by_profile(monkeypatch) -> None:
    from app.services.application import container

    local_store = object()
    production_store = object()
    monkeypatch.setattr(container, "RepositoryStore", lambda: local_store)
    monkeypatch.setattr(container, "ProductionRepositoryStore", lambda: production_store)
    monkeypatch.setattr(settings, "app_env", "local")
    assert container.create_repository_store() is local_store
    monkeypatch.setattr(settings, "app_env", "production")
    assert container.create_repository_store() is production_store


def test_composition_root_selects_queue_only_for_production(monkeypatch) -> None:
    from app.services.application import container

    broker = object()
    queue = object()
    monkeypatch.setattr(container, "create_dramatiq_broker", lambda _url: broker)
    monkeypatch.setattr(container, "DramatiqIndexJobQueue", lambda value: queue if value is broker else None)
    monkeypatch.setattr(settings, "app_env", "local")
    assert container.create_index_job_queue() is None
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/0")
    assert container.create_index_job_queue() is queue


def test_repository_and_evidence_round_trip(production_database, tmp_path: Path, monkeypatch) -> None:
    _, engine, _ = production_database
    monkeypatch.setattr(settings, "repository_storage_dir", tmp_path)
    store = ProductionRepositoryStore(engine)
    repository = _repository(tmp_path)
    store.save_repository(repository)

    loaded = store.list_repositories()
    assert len(loaded) == 1
    assert loaded[0].id == repository.id
    assert loaded[0].source_path == repository.source_path
    assert loaded[0].files[0].path == "app.py"
    assert loaded[0].symbols[0].id == "symbol:v1:hello"
    assert loaded[0].graph_edges[0].source == "node_a"

    evidence = EvidenceDTO(
        evidence_id="evidence_test", repository_id="repo_test", index_version=1, source_type="symbol",
        file_path="app.py", symbol_name="hello", start_line=1, end_line=2, content_preview="def hello()",
        relevance_reason="exact", confidence_score=1.0, retrieval_source="exact",
    )
    store.save_evidence(evidence)
    assert store.get_evidence("evidence_test").file_path == "app.py"
    store.mark_stale_evidence("repo_test", 2)
    assert store.get_evidence("evidence_test").is_stale is True

    store.delete_repository("repo_test")
    assert store.list_repositories() == []


def test_dangling_graph_write_rolls_back(production_database, tmp_path: Path, monkeypatch) -> None:
    _, engine, _ = production_database
    monkeypatch.setattr(settings, "repository_storage_dir", tmp_path)
    store = ProductionRepositoryStore(engine)
    with pytest.raises(ProductionRepositoryError, match="outside the repository index version"):
        store.save_repository(_repository(tmp_path, dangling=True))
    with engine.connect() as connection:
        assert connection.scalar(select(ProductionBase.metadata.tables["repositories"].c.id)) is None


def test_job_target_version_transitions_from_building_to_active(production_database, tmp_path: Path, monkeypatch) -> None:
    _, engine, _ = production_database
    monkeypatch.setattr(settings, "repository_storage_dir", tmp_path)
    store = ProductionRepositoryStore(engine)
    repository = _repository(tmp_path)
    empty = RepositoryState(id=repository.id, name=repository.name, source_type=repository.source_type, source_uri=None, source_path=repository.source_path)
    store.save_repository_metadata(empty)
    job = IndexingJobRecord(id="job_test", repository_id=repository.id, status="running", index_version=1, started_at="2026-07-13T00:00:00+00:00")
    store.save_indexing_job(job)
    assert store.get_indexing_job(repository.id, job.id).index_version == 1
    store.save_repository(repository)
    versions = ProductionBase.metadata.tables["index_versions"]
    with engine.connect() as connection:
        assert connection.scalar(select(versions.c.lifecycle).where(versions.c.repository_id == repository.id)) == "active"


def test_source_path_must_match_managed_repository_root(production_database, tmp_path: Path, monkeypatch) -> None:
    _, engine, _ = production_database
    managed = tmp_path / "managed"
    monkeypatch.setattr(settings, "repository_storage_dir", managed)
    repository = _repository(tmp_path / "external")
    with pytest.raises(ProductionRepositoryError, match="managed production root"):
        ProductionRepositoryStore(engine).save_repository(repository)
