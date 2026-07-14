from __future__ import annotations

import asyncio
import stat
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import DomainError
from app.services.codebase_service import CodebaseService
from app.services.ingestion.archive_service import ArchiveService


@pytest.fixture
def isolated_import_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    upload_root = tmp_path / "uploads"
    repository_root = tmp_path / "repositories"
    monkeypatch.setattr(settings, "upload_storage_dir", upload_root)
    monkeypatch.setattr(settings, "repository_storage_dir", repository_root)
    monkeypatch.setattr(settings, "max_zip_entries", 20)
    monkeypatch.setattr(settings, "max_file_size_mb", 1)
    monkeypatch.setattr(settings, "max_extracted_size_mb", 2)
    monkeypatch.setattr(settings, "max_archive_compression_ratio", 100)
    monkeypatch.setattr(settings, "max_path_depth", 10)
    monkeypatch.setattr(settings, "git_clone_timeout_seconds", 7)
    return upload_root


def _zip_bytes(entries: list[tuple[zipfile.ZipInfo | str, bytes]]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, content in entries:
            archive.writestr(path, content)
    return output.getvalue()


def _extract(content: bytes, tmp_path: Path) -> None:
    archive_path = tmp_path / "source.zip"
    archive_path.write_bytes(content)
    ArchiveService().safe_extract_zip(archive_path, tmp_path / "source")


@pytest.mark.parametrize(
    ("member_name", "expected_code"),
    [
        ("../escape.py", "ARCHIVE_PATH_TRAVERSAL"),
        ("/absolute.py", "ARCHIVE_PATH_TRAVERSAL"),
        ("C:/drive.py", "ARCHIVE_PATH_TRAVERSAL"),
    ],
)
def test_archive_rejects_non_relative_paths(
    member_name: str,
    expected_code: str,
    tmp_path: Path,
    isolated_import_roots: Path,
) -> None:
    with pytest.raises(DomainError) as caught:
        _extract(_zip_bytes([(member_name, b"print('unsafe')")]), tmp_path)

    assert caught.value.code == expected_code


@pytest.mark.parametrize(
    ("mode", "expected_code"),
    [
        (stat.S_IFLNK | 0o777, "ARCHIVE_LINK_NOT_ALLOWED"),
        (stat.S_IFIFO | 0o600, "ARCHIVE_SPECIAL_FILE_NOT_ALLOWED"),
    ],
)
def test_archive_rejects_links_and_special_files(
    mode: int,
    expected_code: str,
    tmp_path: Path,
    isolated_import_roots: Path,
) -> None:
    member = zipfile.ZipInfo("project/item.py")
    member.create_system = 3
    member.external_attr = mode << 16

    with pytest.raises(DomainError) as caught:
        _extract(_zip_bytes([(member, b"target")]), tmp_path)

    assert caught.value.code == expected_code


@pytest.mark.parametrize(
    "paths",
    [
        ("project/App.py", "project/app.py"),
        ("project/caf\N{LATIN SMALL LETTER E WITH ACUTE}.py", "project/cafe\N{COMBINING ACUTE ACCENT}.py"),
    ],
)
def test_archive_rejects_case_and_unicode_path_collisions(
    paths: tuple[str, str],
    tmp_path: Path,
    isolated_import_roots: Path,
) -> None:
    with pytest.raises(DomainError) as caught:
        _extract(_zip_bytes([(paths[0], b"first"), (paths[1], b"second")]), tmp_path)

    assert caught.value.code == "DUPLICATE_ARCHIVE_PATH"


def test_archive_enforces_depth_entry_size_and_ratio_quotas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    isolated_import_roots: Path,
) -> None:
    monkeypatch.setattr(settings, "max_path_depth", 2)
    with pytest.raises(DomainError) as depth:
        _extract(_zip_bytes([("a/b/c.py", b"x")]), tmp_path)
    assert depth.value.code == "ARCHIVE_PATH_TOO_DEEP"

    monkeypatch.setattr(settings, "max_path_depth", 10)
    monkeypatch.setattr(settings, "max_zip_entries", 1)
    with pytest.raises(DomainError) as entries:
        _extract(_zip_bytes([("a.py", b"x"), ("b.py", b"y")]), tmp_path)
    assert entries.value.code == "TOO_MANY_FILES"

    monkeypatch.setattr(settings, "max_zip_entries", 20)
    with pytest.raises(DomainError) as file_size:
        _extract(_zip_bytes([("large.py", b"x" * (1024 * 1024 + 1))]), tmp_path)
    assert file_size.value.code == "IMPORT_FILE_TOO_LARGE"

    monkeypatch.setattr(settings, "max_archive_compression_ratio", 2)
    with pytest.raises(DomainError) as ratio:
        _extract(_zip_bytes([("compressed.py", b"x" * 10_000)]), tmp_path)
    assert ratio.value.code == "ZIP_BOMB_RISK"


def test_archive_counts_actual_streamed_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    isolated_import_roots: Path,
) -> None:
    member = zipfile.ZipInfo("actual.py")
    member.file_size = 1
    member.compress_size = 1

    class FakeZip:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def infolist(self):
            return [member]

        def open(self, _member):
            return BytesIO(b"x" * (1024 * 1024 + 1))

    monkeypatch.setattr(zipfile, "ZipFile", lambda _path: FakeZip())

    with pytest.raises(DomainError) as caught:
        ArchiveService().safe_extract_zip(tmp_path / "unused.zip", tmp_path / "source")

    assert caught.value.code == "IMPORT_FILE_TOO_LARGE"


def test_failed_zip_session_removes_all_staging(
    isolated_import_roots: Path,
) -> None:
    service = CodebaseService()
    upload = UploadFile(BytesIO(_zip_bytes([("../escape.py", b"x")])), filename="unsafe.zip")

    with pytest.raises(DomainError):
        asyncio.run(service.create_zip_import_session(upload, None))

    assert not list((isolated_import_roots / "import_sessions").glob("*"))


def _folder_upload(content: bytes, filename: str) -> UploadFile:
    return UploadFile(BytesIO(content), filename=filename)


def test_folder_rejects_normalized_duplicates_and_cleans_staging(
    isolated_import_roots: Path,
) -> None:
    service = CodebaseService()
    files = [_folder_upload(b"first", "App.py"), _folder_upload(b"second", "app.py")]

    with pytest.raises(DomainError) as caught:
        asyncio.run(service.create_folder_import_session(files, ["src/App.py", "src/app.py"], None))

    assert caught.value.code == "DUPLICATE_IMPORT_PATH"
    assert not list((isolated_import_roots / "import_sessions").glob("*"))


def test_folder_enforces_count_file_and_aggregate_quotas(
    isolated_import_roots: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CodebaseService()
    monkeypatch.setattr(settings, "max_zip_entries", 1)
    with pytest.raises(DomainError) as count:
        asyncio.run(
            service.create_folder_import_session(
                [_folder_upload(b"x", "a.py"), _folder_upload(b"y", "b.py")],
                ["a.py", "b.py"],
                None,
            )
        )
    assert count.value.code == "TOO_MANY_FILES"

    monkeypatch.setattr(settings, "max_zip_entries", 20)
    with pytest.raises(DomainError) as file_size:
        asyncio.run(
            service.create_folder_import_session(
                [_folder_upload(b"x" * (1024 * 1024 + 1), "large.py")],
                ["large.py"],
                None,
            )
        )
    assert file_size.value.code == "IMPORT_FILE_TOO_LARGE"

    monkeypatch.setattr(settings, "max_extracted_size_mb", 1)
    with pytest.raises(DomainError) as aggregate:
        asyncio.run(
            service.create_folder_import_session(
                [_folder_upload(b"x" * 600_000, "a.py"), _folder_upload(b"y" * 600_000, "b.py")],
                ["a.py", "b.py"],
                None,
            )
        )
    assert aggregate.value.code == "REPOSITORY_TOO_LARGE"
    assert not list((isolated_import_roots / "import_sessions").glob("*"))


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repo",
        "https://user@github.com/owner/repo",
        "https://github.com:443/owner/repo",
        "https://github.com:not-a-port/owner/repo",
        "https://github.com/owner/repo?ref=main",
        "https://127.0.0.1/owner/repo",
        "https://github.com/owner/repo/extra",
    ],
)
def test_git_rejects_noncanonical_destinations(url: str, isolated_import_roots: Path) -> None:
    with pytest.raises(DomainError) as caught:
        CodebaseService().create_github_import_session(url, None)

    assert caught.value.code == "INVALID_GITHUB_URL"


@pytest.mark.parametrize("ref", ["--upload-pack=evil", "../main", "main lock", "main~1", "topic.lock"])
def test_git_rejects_unsafe_refs(ref: str, isolated_import_roots: Path) -> None:
    with pytest.raises(DomainError) as caught:
        CodebaseService().create_github_import_session("https://github.com/owner/repo", None, ref)

    assert caught.value.code == "INVALID_GIT_REF"


def test_git_clone_is_hardened_and_metadata_is_removed(
    isolated_import_roots: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        source_dir = Path(command[-1])
        pack_dir = source_dir / ".git" / "objects" / "pack"
        pack_dir.mkdir(parents=True)
        pack_index = pack_dir / "pack-test.idx"
        pack_index.write_bytes(b"git pack index")
        pack_index.chmod(stat.S_IREAD)
        (source_dir / "app.py").write_text("print('safe')", encoding="utf-8")

    monkeypatch.setattr(subprocess, "run", fake_run)
    service = CodebaseService()

    session = service.create_github_import_session("https://github.com/owner/repo.git", None, "main")

    source_dir = service.import_sessions[session.import_session_id].source_path
    command = captured["command"]
    kwargs = captured["kwargs"]
    assert "protocol.allow=never" in command
    assert "protocol.https.allow=always" in command
    assert "http.followRedirects=false" in command
    assert "--depth" in command and "--single-branch" in command and "--no-recurse-submodules" in command
    assert kwargs["timeout"] == 7
    assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert kwargs["env"]["GIT_ALLOW_PROTOCOL"] == "https"
    assert kwargs["env"]["GIT_LFS_SKIP_SMUDGE"] == "1"
    assert not (source_dir / ".git").exists()
    assert (source_dir / "app.py").is_file()


def test_git_timeout_and_post_clone_limits_are_handled_safely(
    isolated_import_roots: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(_command, **_kwargs):
        raise subprocess.TimeoutExpired("git", 7)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(DomainError) as timed_out:
        CodebaseService().create_github_import_session("https://github.com/owner/repo", None)
    assert timed_out.value.code == "GITHUB_IMPORT_TIMEOUT"
    assert not list((isolated_import_roots / "import_sessions").glob("*"))

    def clone_with_large_file(command, **_kwargs):
        source_dir = Path(command[-1])
        (source_dir / ".git").mkdir(parents=True)
        (source_dir / "large.py").write_bytes(b"x" * (1024 * 1024 + 1))
        (source_dir / "app.py").write_text("print('safe')", encoding="utf-8")

    monkeypatch.setattr(subprocess, "run", clone_with_large_file)
    service = CodebaseService()
    session = service.create_github_import_session("https://github.com/owner/repo", None)
    preview = service.get_import_preview(session.import_session_id)

    assert preview.file_statistics.supported_files == 1
    assert preview.file_statistics.skipped_files == 1
    assert any(item.reason == "file_too_large" and item.skipped_count == 1 for item in preview.ignore_summary)
    service.cancel_import_session(session.import_session_id)

    monkeypatch.setattr(settings, "max_extracted_size_mb", 1)

    def aggregate_oversized_clone(command, **_kwargs):
        source_dir = Path(command[-1])
        (source_dir / ".git").mkdir(parents=True)
        (source_dir / "a.py").write_bytes(b"x" * 600_000)
        (source_dir / "b.py").write_bytes(b"y" * 600_000)

    monkeypatch.setattr(subprocess, "run", aggregate_oversized_clone)
    with pytest.raises(DomainError) as aggregate:
        CodebaseService().create_github_import_session("https://github.com/owner/repo", None)
    assert aggregate.value.code == "REPOSITORY_TOO_LARGE"
    assert not list((isolated_import_roots / "import_sessions").glob("*"))


def test_folder_session_accepts_bounded_batches_before_preview(
    isolated_import_roots: Path,
) -> None:
    service = CodebaseService().ingestion
    session = service.start_folder_import_session("sample", total_files=2, total_bytes=2)

    first = asyncio.run(
        service.upload_folder_batch(session.import_session_id, [_folder_upload(b"x", "a.py")], ["sample/a.py"])
    )
    assert first.received_files == 1
    assert service.get_import_session_status(session.import_session_id).stage == "folder_upload_batch"

    with pytest.raises(DomainError) as incomplete:
        service.complete_folder_import_session(session.import_session_id)
    assert incomplete.value.code == "INCOMPLETE_FOLDER_UPLOAD"

    second = asyncio.run(
        service.upload_folder_batch(session.import_session_id, [_folder_upload(b"y", "b.py")], ["sample/b.py"])
    )
    assert second.received_files == 2
    completed = service.complete_folder_import_session(session.import_session_id)
    assert completed.status == "preview_ready"
    assert (isolated_import_roots / "import_sessions" / session.import_session_id / "source" / "sample" / "a.py").is_file()
