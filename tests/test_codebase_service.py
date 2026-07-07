from __future__ import annotations

import asyncio
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.core.errors import DomainError
from app.services.codebase_service import CodebaseService


FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "fastapi_react_sample"


def fixture_upload_files():
    files: list[UploadFile] = []
    relative_paths: list[str] = []
    for path in FIXTURE_REPO.rglob("*"):
        if not path.is_file():
            continue
        files.append(UploadFile(BytesIO(path.read_bytes()), filename=path.name))
        relative_paths.append(path.relative_to(FIXTURE_REPO).as_posix())
    return files, relative_paths


def import_fixture_folder(service: CodebaseService, name: str):
    files, relative_paths = fixture_upload_files()
    return asyncio.run(service.upload_folder(files, relative_paths, name))


def upload_zip_bytes(service: CodebaseService, filename: str, content: bytes, name: str | None = None):
    return asyncio.run(service.upload_zip(UploadFile(BytesIO(content), filename=filename), name))


def make_zip(entries: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def make_zip_with_duplicate_path() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("project/app.py", "print('first')\n")
        archive.writestr("project/app.py", "print('second')\n")
    return buffer.getvalue()


def test_service_indexes_fixture_and_answers_with_evidence() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-service-test")

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
    assert chat.citations[0].index_version == 1
    assert evidence.index_version == 1
    assert not evidence.is_stale


def test_service_file_tree_and_content_are_available_after_index() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-file-test")

    service.start_indexing(created.repository_id, force_reindex=True)
    tree = service.get_file_tree(created.repository_id)
    content = service.get_file_content(created.repository_id, "backend/app/main.py")

    assert tree
    assert content.language == "python"
    assert "FastAPI" in content.content


def test_import_session_preview_and_confirm_creates_indexed_repository() -> None:
    service = CodebaseService()
    files, relative_paths = fixture_upload_files()

    session = asyncio.run(service.create_folder_import_session(files, relative_paths, "fixture-import-session-test"))
    preview_response = service.get_import_preview(session.import_session_id)
    confirmed = service.confirm_import_session(session.import_session_id, None, True)

    assert session.status == "preview_ready"
    assert session.source_type == "upload_folder"
    assert preview_response.status == "preview_ready"
    assert preview_response.file_statistics.supported_files >= 8
    assert "FastAPI" in preview_response.detected_stack
    assert confirmed.repository_id in service.repositories
    assert confirmed.indexing_job_id
    assert confirmed.status == "indexed"
    assert confirmed.index_version == 1


def test_import_preview_is_cached_after_first_scan() -> None:
    service = CodebaseService()
    files, relative_paths = fixture_upload_files()

    session = asyncio.run(service.create_folder_import_session(files, relative_paths, "fixture-preview-cache-test"))
    first_preview = service.get_import_preview(session.import_session_id)

    def fail_scan(_repository):
        raise RuntimeError("preview should be served from cache")

    service.scanner.scan_files_with_diagnostics = fail_scan
    second_preview = service.get_import_preview(session.import_session_id)

    assert second_preview.file_statistics == first_preview.file_statistics
    assert second_preview.project_summary == first_preview.project_summary


def test_import_preview_detects_duplicate_by_project_fingerprint() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-duplicate-source")
    service.start_indexing(created.repository_id, force_reindex=True)
    files, relative_paths = fixture_upload_files()

    session = asyncio.run(service.create_folder_import_session(files, relative_paths, "fixture-duplicate-source-copy"))
    preview = service.get_import_preview(session.import_session_id)

    assert any(item.match_reason == "same_fingerprint" for item in preview.possible_duplicates)


def test_github_import_session_prepares_preview_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    service = CodebaseService()

    def fake_clone(_clone_url: str, source_dir: Path, _branch: str | None = None) -> None:
        source_dir.mkdir(parents=True)
        (source_dir / ".git").mkdir()
        (source_dir / "app.py").write_text("print('github preview')\n", encoding="utf-8")

    monkeypatch.setattr(service.ingestion, "_clone_github_repository", fake_clone)

    session = service.create_github_import_session("https://github.com/example/demo", None)
    preview = service.get_import_preview(session.import_session_id)

    assert session.status == "preview_ready"
    assert session.source_type == "github_url"
    assert preview.project_summary.suggested_name == "demo"
    assert preview.file_statistics.supported_files == 1
    assert not (service.import_sessions[session.import_session_id].source_path / ".git").exists()


def test_github_import_session_rejects_non_github_url() -> None:
    service = CodebaseService()

    with pytest.raises(DomainError) as error:
        service.create_github_import_session("https://example.com/not/github", None)

    assert error.value.code == "INVALID_GITHUB_URL"


def test_import_session_cancel_removes_temporary_source() -> None:
    service = CodebaseService()
    files, relative_paths = fixture_upload_files()

    session = asyncio.run(service.create_folder_import_session(files, relative_paths, "fixture-cancel-session-test"))
    source_path = service.import_sessions[session.import_session_id].source_path
    cancelled = service.cancel_import_session(session.import_session_id)

    assert cancelled.cancelled
    assert cancelled.import_session_id == session.import_session_id
    assert session.import_session_id not in service.import_sessions
    assert not source_path.exists()


def test_indexing_job_persists_and_status_survives_service_restart() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-job-test")

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
    created = import_fixture_folder(service, "fixture-reindex-test")

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
    assert second_status.index_version == first_status.index_version + 1


def test_failed_reindex_retains_previous_index() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-retain-index-test")

    service.start_indexing(created.repository_id, force_reindex=True)
    first_overview = service.get_overview(created.repository_id)

    def fail_parse(_repository):
        raise RuntimeError("parser failed")

    service.parser.parse_files = fail_parse
    with pytest.raises(RuntimeError):
        service.start_indexing(created.repository_id, force_reindex=True)

    retained_overview = service.get_overview(created.repository_id)
    failed_status = service.get_index_status(created.repository_id)

    assert service.repositories[created.repository_id].status == "indexed"
    assert failed_status.status == "failed"
    assert retained_overview.stats == first_overview.stats


def test_upload_zip_filters_unsafe_content_and_hides_internal_source_uri() -> None:
    service = CodebaseService()
    content = make_zip(
        {
            "project/app/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "project/.env": "SECRET=do-not-index\n",
            "project/node_modules/pkg/index.js": "console.log('skip')\n",
            "project/archive.bin": "skip",
        }
    )

    created = upload_zip_bytes(service, "sample.zip", content, None)
    repository = service.repositories[created.repository_id]
    listed = next(item for item in service.list_repositories() if item.id == created.repository_id)

    assert listed.source_uri is None
    assert listed.source_label == "sample.zip"
    assert (repository.source_path / "project" / "app" / "main.py").exists()
    assert not (repository.source_path / "project" / ".env").exists()
    assert not (repository.source_path / "project" / "node_modules").exists()
    assert not (repository.source_path / "project" / "archive.bin").exists()


def test_upload_zip_rejects_path_traversal() -> None:
    service = CodebaseService()
    content = make_zip({"../escape.py": "print('escape')\n"})

    with pytest.raises(DomainError) as error:
        upload_zip_bytes(service, "unsafe.zip", content, None)

    assert error.value.code == "ARCHIVE_PATH_TRAVERSAL"


def test_upload_zip_rejects_duplicate_paths() -> None:
    service = CodebaseService()

    with pytest.raises(DomainError) as error:
        upload_zip_bytes(service, "duplicate.zip", make_zip_with_duplicate_path(), None)

    assert error.value.code == "DUPLICATE_ARCHIVE_PATH"


def test_upload_zip_reports_nested_archive_as_skipped() -> None:
    service = CodebaseService()
    nested = make_zip({"nested/app.py": "print('nested')\n"})
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("project/app.py", "print('ok')\n")
        archive.writestr("project/vendor.zip", nested)

    session = asyncio.run(service.create_zip_import_session(UploadFile(BytesIO(buffer.getvalue()), filename="nested.zip"), "nested-archive-test"))
    preview = service.get_import_preview(session.import_session_id)

    assert any(item.reason == "nested_archive" for item in preview.ignore_summary)


def test_reindex_marks_existing_evidence_as_stale() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-stale-evidence-test")

    service.start_indexing(created.repository_id, force_reindex=True)
    chat = service.chat(created.repository_id, "login flow")
    evidence = service.get_evidence(created.repository_id, chat.citations[0].evidence_id)

    service.start_indexing(created.repository_id, force_reindex=True)
    stale_evidence = service.get_evidence(created.repository_id, evidence.evidence_id)

    assert evidence.index_version == 1
    assert stale_evidence.index_version == 1
    assert stale_evidence.is_stale


def test_search_results_include_current_evidence_metadata() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-search-metadata-test")

    service.start_indexing(created.repository_id, force_reindex=True)
    response = service.search(created.repository_id, "login")

    assert response.results
    assert response.results[0].index_version == 1
    assert not response.results[0].is_stale


def test_validate_evidence_reports_valid_and_stale_items() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-validate-evidence-test")

    service.start_indexing(created.repository_id, force_reindex=True)
    search = service.search(created.repository_id, "login")
    evidence_id = search.results[0].evidence_id

    valid_response = service.validate_evidence(created.repository_id, [evidence_id, "ev_missing"])
    valid_by_id = {item.evidence_id: item for item in valid_response.items}

    assert valid_by_id[evidence_id].is_valid
    assert not valid_by_id[evidence_id].is_stale
    assert not valid_by_id["ev_missing"].is_valid
    assert valid_by_id["ev_missing"].reason == "evidence_not_found"

    service.start_indexing(created.repository_id, force_reindex=True)
    stale_response = service.validate_evidence(created.repository_id, [evidence_id])

    assert not stale_response.items[0].is_valid
    assert stale_response.items[0].is_stale
    assert stale_response.items[0].reason == "stale_index_version"


def test_ask_with_selected_evidence_requires_valid_evidence() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-ask-with-evidence-test")

    service.start_indexing(created.repository_id, force_reindex=True)
    search = service.search(created.repository_id, "login")
    evidence_id = search.results[0].evidence_id

    answer = service.ask_with_evidence(created.repository_id, "Explain this login evidence.", [evidence_id], "conv_test")

    assert answer.conversation_id == "conv_test"
    assert answer.evidence_sufficient
    assert answer.citations[0].evidence_id == evidence_id

    service.start_indexing(created.repository_id, force_reindex=True)
    stale_answer = service.ask_with_evidence(created.repository_id, "Explain stale evidence.", [evidence_id], None)

    assert not stale_answer.evidence_sufficient
    assert stale_answer.citations == []
    assert any("stale_index_version" in item for item in stale_answer.missing_evidence)


def test_delete_repository_removes_project_records_and_managed_source() -> None:
    service = CodebaseService()
    created = import_fixture_folder(service, "fixture-delete-test")
    managed_source = service.repositories[created.repository_id].source_path
    service.start_indexing(created.repository_id, force_reindex=True)
    chat = service.chat(created.repository_id, "login flow")
    evidence_id = chat.citations[0].evidence_id

    deleted = service.delete_repository(created.repository_id)

    assert deleted.deleted
    assert deleted.repository_id == created.repository_id
    assert FIXTURE_REPO.exists()
    assert not managed_source.exists()
    assert all(repository.id != created.repository_id for repository in service.list_repositories())
    with pytest.raises(DomainError) as overview_error:
        service.get_overview(created.repository_id)
    assert overview_error.value.code == "REPOSITORY_NOT_FOUND"
    with pytest.raises(DomainError) as evidence_error:
        service.get_evidence(created.repository_id, evidence_id)
    assert evidence_error.value.code == "EVIDENCE_NOT_FOUND"

    restarted = CodebaseService()
    assert all(repository.id != created.repository_id for repository in restarted.list_repositories())
