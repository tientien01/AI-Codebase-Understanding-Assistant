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
