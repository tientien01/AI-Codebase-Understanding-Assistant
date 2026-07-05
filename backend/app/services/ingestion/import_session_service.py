from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import DomainError
from app.schemas.api import (
    ImportCancelResponse,
    ImportConfirmResponse,
    ImportDuplicateCandidateDTO,
    ImportFileStatisticsDTO,
    ImportPreviewResponse,
    ImportProjectSummaryDTO,
    ImportSessionCreateResponse,
    RepositoryCreateResponse,
)
from app.services.index_models import ImportSessionRecord, RepositoryState
from app.services.indexing.indexing_service import IndexingService
from app.services.ingestion.archive_service import ArchiveService
from app.services.ingestion.streaming_upload_service import StreamingUploadService
from app.services.ingestion.upload_service import UploadService
from app.services.repositories.repository_service import RepositoryService
from app.services.scanning.scanner_service import ScannerService
from app.services.text_utils import utc_now


class ImportSessionService:
    def __init__(
        self,
        repositories: RepositoryService,
        indexing: IndexingService,
        scanner: ScannerService,
        archive: ArchiveService,
        upload: UploadService,
    ) -> None:
        self.repositories = repositories
        self.indexing = indexing
        self.scanner = scanner
        self.archive = archive
        self.upload = upload
        self.streaming_upload = StreamingUploadService()
        self.import_sessions: dict[str, ImportSessionRecord] = {}

    async def upload_zip(self, file: UploadFile, name: str | None) -> RepositoryCreateResponse:
        session = await self.create_zip_import_session(file, name)
        confirmed = self.confirm_import_session(session.import_session_id, name, start_indexing=False)
        self.import_sessions.pop(session.import_session_id, None)
        repository = self.repositories.get_repository(confirmed.repository_id)
        return RepositoryCreateResponse(
            repository_id=repository.id,
            name=repository.name,
            status=repository.status,
            source_type=repository.source_type,
        )

    async def upload_folder(
        self,
        files: list[UploadFile],
        relative_paths: list[str],
        name: str | None,
    ) -> RepositoryCreateResponse:
        session = await self.create_folder_import_session(files, relative_paths, name)
        confirmed = self.confirm_import_session(session.import_session_id, name, start_indexing=False)
        self.import_sessions.pop(session.import_session_id, None)
        repository = self.repositories.get_repository(confirmed.repository_id)
        return RepositoryCreateResponse(
            repository_id=repository.id,
            name=repository.name,
            status=repository.status,
            source_type=repository.source_type,
        )

    async def create_zip_import_session(self, file: UploadFile, name: str | None) -> ImportSessionCreateResponse:
        if not file.filename or not file.filename.endswith(".zip"):
            raise DomainError("INVALID_ARCHIVE", "Only .zip repositories are supported.", 400)

        session_id = f"import_{uuid4().hex[:10]}"
        session_root = settings.upload_storage_dir / "import_sessions" / session_id
        source_dir = session_root / "source"
        session_root.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)
        zip_path = session_root / "source.zip"
        max_upload_size = settings.max_upload_size_mb * 1024 * 1024
        await self.streaming_upload.save_upload(file, zip_path, max_upload_size)

        skipped_records: list[dict[str, str | None]] = []
        security_records: list[dict[str, str]] = []
        try:
            extracted_files = self.archive.safe_extract_zip(zip_path, source_dir, skipped_records, security_records)
        except zipfile.BadZipFile as exc:
            raise DomainError("INVALID_ARCHIVE", "Uploaded file is not a valid zip archive.", 400) from exc
        if extracted_files == 0:
            raise DomainError("NO_SUPPORTED_FILES", "Archive contains no supported non-secret files.", 400)

        session = ImportSessionRecord(
            id=session_id,
            name=name or Path(file.filename).stem,
            source_type="upload_zip",
            source_uri=str(zip_path),
            source_label=file.filename,
            source_path=source_dir,
            status="preview_ready",
            created_at=utc_now(),
            skipped_file_records=skipped_records,
            security_warning_records=security_records,
        )
        self.import_sessions[session.id] = session
        return ImportSessionCreateResponse(import_session_id=session.id, status="created", source_type=session.source_type)

    async def create_folder_import_session(
        self,
        files: list[UploadFile],
        relative_paths: list[str],
        name: str | None,
    ) -> ImportSessionCreateResponse:
        if not files:
            raise DomainError("INVALID_REPOSITORY", "No files were uploaded.", 400)
        if len(files) != len(relative_paths):
            raise DomainError("INVALID_REPOSITORY", "Uploaded files and relative paths do not match.", 400)

        session_id = f"import_{uuid4().hex[:10]}"
        source_dir = settings.upload_storage_dir / "import_sessions" / session_id / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        saved_files = 0
        skipped_records: list[dict[str, str | None]] = []
        security_records: list[dict[str, str]] = []
        for upload, relative_path in zip(files, relative_paths, strict=True):
            safe_path = self.upload.safe_upload_relative_path(
                relative_path or upload.filename or "",
                skipped_records,
                security_records,
            )
            if safe_path is None:
                continue
            target = (source_dir / safe_path).resolve()
            if not self.upload.is_relative_to(target, source_dir.resolve()):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                await self.streaming_upload.save_upload(
                    upload,
                    target,
                    settings.max_file_size_mb * 1024 * 1024,
                )
            except DomainError as exc:
                if exc.code != "UPLOAD_TOO_LARGE":
                    raise
                self.archive.record_skipped(
                    skipped_records,
                    safe_path.as_posix(),
                    "file_too_large",
                    f">{settings.max_file_size_mb}MB",
                )
                continue
            saved_files += 1

        if saved_files == 0:
            raise DomainError("INVALID_REPOSITORY", "No supported non-secret files were uploaded.", 400)

        source_label = name or Path(relative_paths[0]).parts[0]
        session = ImportSessionRecord(
            id=session_id,
            name=source_label,
            source_type="upload_folder",
            source_uri=str(source_dir),
            source_label=source_label,
            source_path=source_dir,
            status="preview_ready",
            created_at=utc_now(),
            skipped_file_records=skipped_records,
            security_warning_records=security_records,
        )
        self.import_sessions[session.id] = session
        return ImportSessionCreateResponse(import_session_id=session.id, status="created", source_type=session.source_type)

    def get_import_preview(self, import_session_id: str) -> ImportPreviewResponse:
        session = self._get_import_session(import_session_id)
        preview_repository = RepositoryState(
            id=session.id,
            name=session.name,
            source_type=session.source_type,
            source_uri=session.source_uri,
            source_label=session.source_label,
            source_path=session.source_path,
            status="previewed",
        )
        scan_result = self.scanner.scan_files_with_diagnostics(preview_repository)
        preview_repository.files = scan_result.files
        repository_size = sum(path.stat().st_size for path in session.source_path.rglob("*") if path.is_file())
        file_statistics = self._import_file_statistics(preview_repository)
        file_statistics.total_files += len(session.skipped_file_records)
        file_statistics.skipped_files += len(session.skipped_file_records)
        skipped_records = [
            *session.skipped_file_records,
            *[
                {
                    "file_path": skipped.file_path,
                    "reason": skipped.reason,
                    "matched_pattern": skipped.matched_pattern,
                }
                for skipped in scan_result.skipped_files
            ],
        ]
        return ImportPreviewResponse(
            import_session_id=session.id,
            status=session.status,
            project_summary=ImportProjectSummaryDTO(
                suggested_name=session.name,
                source_type=session.source_type,
                repository_size_bytes=repository_size,
                estimated_index_time_seconds=max(1, file_statistics.supported_files // 25),
            ),
            detected_stack=self.repositories.detect_stack(preview_repository),
            file_statistics=file_statistics,
            folder_preview=self._folder_preview(session.source_path),
            ignore_summary=self._ignore_summary(skipped_records),
            security_warnings=[
                {
                    "file_path": warning["file_path"],
                    "risk_type": warning["risk_type"],
                    "action": warning["action"],
                }
                for warning in [
                    *session.security_warning_records,
                    *[
                        {
                            "file_path": item.file_path,
                            "risk_type": item.risk_type,
                            "action": item.action,
                        }
                        for item in scan_result.security_warnings
                    ],
                ]
            ],
            indexing_plan=["scan_files", "parse_symbols", "create_chunks", "build_graph", "validate_citations"],
            possible_duplicates=self._possible_import_duplicates(session),
        )

    def confirm_import_session(
        self,
        import_session_id: str,
        name: str | None,
        start_indexing: bool,
        duplicate_action: str = "import_as_new",
    ) -> ImportConfirmResponse:
        session = self._get_import_session(import_session_id)
        if duplicate_action == "cancel":
            return ImportConfirmResponse(repository_id="", indexing_job_id=None, status="cancelled", index_version=None)
        if duplicate_action not in {"import_as_new"}:
            raise DomainError("UNSUPPORTED_OPERATION", "Only import_as_new duplicate action is supported in this milestone.", 400)
        if session.status == "confirmed" and session.confirmed_repository_id:
            repository = self.repositories.get_repository(session.confirmed_repository_id)
            return ImportConfirmResponse(
                repository_id=repository.id,
                indexing_job_id=None,
                status=repository.status,
                index_version=repository.current_index_version,
            )

        repository_id = f"repo_{uuid4().hex[:10]}"
        source_dir = settings.repository_storage_dir / repository_id / "source"
        source_dir.parent.mkdir(parents=True, exist_ok=True)
        if source_dir.exists():
            raise DomainError("INVALID_REPOSITORY", "Repository source destination already exists.", 409)
        shutil.move(str(session.source_path), str(source_dir))

        repository = RepositoryState(
            id=repository_id,
            name=name or session.name,
            source_type=session.source_type,
            source_uri=session.source_uri,
            source_label=session.source_label,
            source_path=source_dir,
        )
        self.repositories.create_repository(repository)
        session.status = "confirmed"
        session.confirmed_repository_id = repository.id

        indexing_job_id = None
        if start_indexing:
            result = self.indexing.start_indexing(repository.id, force_reindex=True)
            indexing_job_id = result.indexing_job_id
        return ImportConfirmResponse(
            repository_id=repository.id,
            indexing_job_id=indexing_job_id,
            status=repository.status,
            index_version=repository.current_index_version,
        )

    def cancel_import_session(self, import_session_id: str) -> ImportCancelResponse:
        session = self._get_import_session(import_session_id)
        session.status = "cancelled"
        session_root = settings.upload_storage_dir / "import_sessions" / session.id
        if session_root.exists() and self.archive.is_relative_to(session_root.resolve(), settings.upload_storage_dir.resolve()):
            shutil.rmtree(session_root)
        self.import_sessions.pop(session.id, None)
        return ImportCancelResponse(cancelled=True, import_session_id=import_session_id)

    def _get_import_session(self, import_session_id: str) -> ImportSessionRecord:
        session = self.import_sessions.get(import_session_id)
        if session is None:
            raise DomainError("IMPORT_SESSION_NOT_FOUND", "Import session not found.", 404, {"import_session_id": import_session_id})
        if session.status in {"cancelled", "expired", "failed"}:
            raise DomainError("IMPORT_SESSION_NOT_AVAILABLE", "Import session is not available.", 409, {"import_session_id": import_session_id})
        return session

    def _import_file_statistics(self, repository: RepositoryState) -> ImportFileStatisticsDTO:
        total_files = sum(1 for path in repository.source_path.rglob("*") if path.is_file())
        language_files: dict[str, int] = {}
        for file in repository.files:
            language_files[file.language] = language_files.get(file.language, 0) + 1
        return ImportFileStatisticsDTO(
            total_files=total_files,
            supported_files=len(repository.files),
            skipped_files=max(0, total_files - len(repository.files)),
            language_files=language_files,
            python_files=len([file for file in repository.files if file.language == "python"]),
            javascript_files=len([file for file in repository.files if file.language == "javascript"]),
            typescript_files=len([file for file in repository.files if file.language == "typescript"]),
            markdown_files=len([file for file in repository.files if file.language == "markdown"]),
            config_files=len([file for file in repository.files if file.file_type == "config"]),
        )

    def _folder_preview(self, source_path: Path) -> list[str]:
        items = []
        for child in sorted(source_path.iterdir(), key=lambda item: item.name.lower()):
            suffix = "/" if child.is_dir() else ""
            items.append(f"{child.name}{suffix}")
            if len(items) >= 12:
                break
        return items

    def _ignore_summary(self, skipped_files) -> list[dict[str, str | int]]:
        counts: dict[tuple[str, str], int] = {}
        for skipped in skipped_files:
            if isinstance(skipped, dict):
                reason = str(skipped.get("reason") or "skipped")
                pattern = str(skipped.get("matched_pattern") or reason)
            else:
                reason = skipped.reason
                pattern = skipped.matched_pattern or skipped.reason
            key = (pattern, reason)
            counts[key] = counts.get(key, 0) + 1
        return [
            {"pattern": pattern, "skipped_count": count, "reason": reason}
            for (pattern, reason), count in sorted(counts.items())
        ]

    def _possible_import_duplicates(self, session: ImportSessionRecord) -> list[ImportDuplicateCandidateDTO]:
        session_name = session.name.lower()
        session_label = (session.source_label or "").lower()
        duplicates = []
        for repository in self.repositories.repositories.values():
            if repository.name.lower() == session_name:
                duplicates.append(
                    ImportDuplicateCandidateDTO(
                        repository_id=repository.id,
                        name=repository.name,
                        match_reason="same_name",
                    )
                )
            elif session_label and (repository.source_label or "").lower() == session_label:
                duplicates.append(
                    ImportDuplicateCandidateDTO(
                        repository_id=repository.id,
                        name=repository.name,
                        match_reason="same_source_label",
                    )
                )
        return duplicates[:5]
