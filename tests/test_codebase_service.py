from __future__ import annotations

from pathlib import Path

from app.services.codebase_service import CodebaseService


FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "fastapi_react_sample"


def test_service_indexes_fixture_and_answers_with_evidence() -> None:
    service = CodebaseService()
    created = service.import_local("fixture-service-test", str(FIXTURE_REPO))

    service.start_indexing(created.repository_id, force_reindex=True)
    overview = service.get_overview(created.repository_id)

    assert overview.stats["files"] >= 8
    assert overview.stats["endpoints"] >= 1
    assert any(endpoint.path == "/login" for endpoint in overview.endpoints)

    chat = service.chat(created.repository_id, "login flow hoat dong nhu the nao?")

    assert chat.evidence_sufficient
    assert chat.citations
    evidence = service.get_evidence(created.repository_id, chat.citations[0].evidence_id)
    assert evidence.repository_id == created.repository_id
    assert evidence.file_path


def test_service_file_tree_and_content_are_available_after_index() -> None:
    service = CodebaseService()
    created = service.import_local("fixture-file-test", str(FIXTURE_REPO))

    service.start_indexing(created.repository_id, force_reindex=True)
    tree = service.get_file_tree(created.repository_id)
    content = service.get_file_content(created.repository_id, "backend/app/main.py")

    assert tree
    assert content.language == "python"
    assert "FastAPI" in content.content


def test_indexing_job_persists_and_status_survives_service_restart() -> None:
    service = CodebaseService()
    created = service.import_local("fixture-job-test", str(FIXTURE_REPO))

    result = service.start_indexing(created.repository_id, force_reindex=True)
    status = service.get_index_status(created.repository_id)

    assert result["indexing_job_id"] == status.job_id
    assert status.status == "completed"
    assert status.progress == 100
    assert status.stats["chunks"] > 0

    restarted = CodebaseService()
    restarted_status = restarted.get_index_status(created.repository_id)

    assert restarted_status.job_id == status.job_id
    assert restarted_status.status == "completed"
    assert restarted_status.total_files == status.total_files


def test_force_reindex_replaces_index_records_without_duplicates() -> None:
    service = CodebaseService()
    created = service.import_local("fixture-reindex-test", str(FIXTURE_REPO))

    service.start_indexing(created.repository_id, force_reindex=True)
    first_overview = service.get_overview(created.repository_id)
    first_status = service.get_index_status(created.repository_id)

    service.start_indexing(created.repository_id, force_reindex=True)
    second_overview = service.get_overview(created.repository_id)
    second_status = service.get_index_status(created.repository_id)

    assert second_status.job_id != first_status.job_id
    assert second_status.status == "completed"
    assert second_overview.stats["files"] == first_overview.stats["files"]
    assert second_overview.stats["endpoints"] == first_overview.stats["endpoints"]
    assert second_overview.stats["chunks"] == first_overview.stats["chunks"]
