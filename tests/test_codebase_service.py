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


def import_fixture_folder(service: CodebaseService, name: str):
    files: list[UploadFile] = []
    relative_paths: list[str] = []
    for path in FIXTURE_REPO.rglob("*"):
        if not path.is_file():
            continue
        files.append(UploadFile(BytesIO(path.read_bytes()), filename=path.name))
        relative_paths.append(path.relative_to(FIXTURE_REPO).as_posix())
    return asyncio.run(service.upload_folder(files, relative_paths, name))


def upload_zip_bytes(service: CodebaseService, filename: str, content: bytes, name: str | None = None):
    return asyncio.run(service.upload_zip(UploadFile(BytesIO(content), filename=filename), name))


def make_zip(entries: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
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
