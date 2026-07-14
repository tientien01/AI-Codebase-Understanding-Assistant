from __future__ import annotations

import hashlib
import math
import os
import re
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse
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
    ImportSessionStatusResponse,
    RepositoryCreateResponse,
)
from app.schemas.imports import FolderImportBatchResponse
from app.services.index_models import FileRecord, ImportSessionRecord, RepositoryState
from app.services.indexing.indexing_service import IndexingService
from app.services.ingestion.archive_service import ArchiveService
from app.services.ingestion.import_policy import ImportQuota, ensure_unique_path, normalized_relative_path
from app.services.ingestion.streaming_upload_service import StreamingUploadService
from app.services.ingestion.upload_service import UploadService
from app.services.repositories.repository_service import RepositoryService
from app.services.scanning.scanner_service import ScanResult, ScannerService
from app.services.text_utils import utc_now


_GITHUB_OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
_GITHUB_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]{1,100}")


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
        activity_logs: list[dict[str, str | dict[str, str]]] = []
        self._append_activity_log(
            activity_logs,
            "upload_received",
            "ZIP upload received.",
            source_label=file.filename,
        )
        session_root = settings.upload_storage_dir / "import_sessions" / session_id
        source_dir = session_root / "source"
        session_root.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)
        zip_path = session_root / "source.zip"
        max_upload_size = settings.max_upload_size_mb * 1024 * 1024
        skipped_records: list[dict[str, str | None]] = []
        security_records: list[dict[str, str]] = []
        try:
            await self.streaming_upload.save_upload(file, zip_path, max_upload_size)
            self._append_activity_log(activity_logs, "upload_saved", "ZIP upload saved to temporary storage.")
            extracted_files = self.archive.safe_extract_zip(zip_path, source_dir, skipped_records, security_records)
        except zipfile.BadZipFile as exc:
            self._cleanup_session_root(session_root)
            raise DomainError("INVALID_ARCHIVE", "Uploaded file is not a valid zip archive.", 400) from exc
        except Exception:
            self._cleanup_session_root(session_root)
            raise
        if extracted_files == 0:
            self._cleanup_session_root(session_root)
            raise DomainError("NO_SUPPORTED_FILES", "Archive contains no supported non-secret files.", 400)
        self._append_activity_log(
            activity_logs,
            "archive_extracted",
            "ZIP archive extracted for preview.",
            extracted_files=extracted_files,
            skipped_files=len(skipped_records),
            security_warnings=len(security_records),
        )

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
            activity_logs=activity_logs,
        )
        self._log_session(session, "preview_ready", "Import session is ready for preview.")
        self.import_sessions[session.id] = session
        return ImportSessionCreateResponse(import_session_id=session.id, status=session.status, source_type=session.source_type)

    async def create_folder_import_session(
        self,
        files: list[UploadFile],
        relative_paths: list[str],
        name: str | None,
    ) -> ImportSessionCreateResponse:
        if not files:
            raise DomainError("INVALID_REPOSITORY", "No files were uploaded.", 400)
        total_bytes = sum(max(0, int(upload.size or 0)) for upload in files)
        session = self.start_folder_import_session(name or Path(relative_paths[0]).parts[0], len(files), total_bytes)
        try:
            await self.upload_folder_batch(session.import_session_id, files, relative_paths)
            return self.complete_folder_import_session(session.import_session_id)
        except Exception:
            self._discard_folder_session(session.import_session_id)
            raise

    def start_folder_import_session(self, name: str, total_files: int, total_bytes: int) -> ImportSessionCreateResponse:
        """Create a resumable folder session before bounded multipart batches arrive."""

        quota = ImportQuota.configured()
        if total_files <= 0:
            raise DomainError("INVALID_REPOSITORY", "No files were selected for upload.", 400)
        if total_files > quota.max_files:
            raise DomainError("TOO_MANY_FILES", "Folder contains more files than the configured limit.", 413)
        if total_bytes < 0 or total_bytes > quota.max_total_bytes:
            raise DomainError("REPOSITORY_TOO_LARGE", "Folder is larger than the configured limit.", 413)

        session_id = f"import_{uuid4().hex[:10]}"
        source_dir = settings.upload_storage_dir / "import_sessions" / session_id / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        session = ImportSessionRecord(
            id=session_id,
            name=name,
            source_type="upload_folder",
            source_uri=str(source_dir),
            source_label=name,
            source_path=source_dir,
            status="uploading",
            created_at=utc_now(),
            expected_file_count=total_files,
            expected_total_bytes=total_bytes,
        )
        self._log_session(
            session,
            "folder_manifest_received",
            "Folder manifest validated. Ready to receive files.",
            total_files=total_files,
            total_bytes=total_bytes,
        )
        self.import_sessions[session.id] = session
        return ImportSessionCreateResponse(import_session_id=session.id, status=session.status, source_type=session.source_type)

    async def upload_folder_batch(
        self,
        import_session_id: str,
        files: list[UploadFile],
        relative_paths: list[str],
    ) -> FolderImportBatchResponse:
        session = self._get_import_session(import_session_id)
        if session.source_type != "upload_folder" or session.status != "uploading":
            raise DomainError("IMPORT_SESSION_NOT_UPLOADABLE", "Folder import session is not accepting files.", 409)
        if not files or len(files) != len(relative_paths):
            raise DomainError("INVALID_REPOSITORY", "Uploaded files and relative paths do not match.", 400)
        if len(files) > 500:
            raise DomainError("UPLOAD_BATCH_TOO_LARGE", "Upload batches are limited to 500 files.", 413)
        if session.received_file_count + len(files) > session.expected_file_count:
            raise DomainError("TOO_MANY_FILES", "Folder upload contains more files than its manifest.", 413)

        quota = ImportQuota.configured()
        quota.files = session.saved_file_count
        quota.total_bytes = session.received_total_bytes
        try:
            for upload, relative_path in zip(files, relative_paths, strict=True):
                submitted_path = normalized_relative_path(relative_path or upload.filename or "")
                ensure_unique_path(submitted_path, session.seen_path_identities)
                safe_path = self.upload.safe_upload_relative_path(
                    submitted_path.as_posix(),
                    session.skipped_file_records,
                    session.security_warning_records,
                )
                session.received_file_count += 1
                if safe_path is None:
                    continue
                target = (session.source_path / safe_path).resolve()
                if not self.upload.is_relative_to(target, session.source_path.resolve()):
                    raise DomainError("UNSAFE_IMPORT_PATH", "Folder upload contains an unsafe path.", 400)
                target.parent.mkdir(parents=True, exist_ok=True)
                remaining_bytes = quota.max_total_bytes - quota.total_bytes
                limit_bytes = min(quota.max_file_bytes, remaining_bytes)
                if limit_bytes <= 0:
                    raise DomainError("REPOSITORY_TOO_LARGE", "Folder upload is larger than the configured limit.", 413)
                total_limited = remaining_bytes < quota.max_file_bytes
                saved_bytes = await self.streaming_upload.save_upload(
                    upload,
                    target,
                    limit_bytes,
                    limit_error_code="REPOSITORY_TOO_LARGE" if total_limited else "IMPORT_FILE_TOO_LARGE",
                    limit_error_message=(
                        "Folder upload is larger than the configured limit."
                        if total_limited
                        else "Folder upload contains a file larger than the configured limit."
                    ),
                )
                quota.add_file(saved_bytes)
                session.received_total_bytes = quota.total_bytes
                session.saved_file_count += 1
        except Exception:
            self._discard_folder_session(import_session_id)
            raise

        self._log_session(
            session,
            "folder_upload_batch",
            "Folder upload batch saved.",
            received_files=session.received_file_count,
            total_files=session.expected_file_count,
        )
        return FolderImportBatchResponse(
            import_session_id=session.id,
            received_files=session.received_file_count,
            total_files=session.expected_file_count,
            status=session.status,
        )

    def complete_folder_import_session(self, import_session_id: str) -> ImportSessionCreateResponse:
        session = self._get_import_session(import_session_id)
        if session.source_type != "upload_folder" or session.status != "uploading":
            raise DomainError("IMPORT_SESSION_NOT_UPLOADABLE", "Folder import session cannot be completed.", 409)
        if session.received_file_count != session.expected_file_count:
            raise DomainError("INCOMPLETE_FOLDER_UPLOAD", "Folder upload is incomplete. Retry the missing batch.", 409)
        if session.saved_file_count == 0:
            self._discard_folder_session(import_session_id)
            raise DomainError("INVALID_REPOSITORY", "No supported non-secret files were uploaded.", 400)

        session.status = "preview_ready"
        self._log_session(
            session,
            "folder_saved",
            "Folder upload is ready for preview.",
            submitted_files=session.received_file_count,
            saved_files=session.saved_file_count,
            skipped_files=len(session.skipped_file_records),
            security_warnings=len(session.security_warning_records),
        )
        self._log_session(session, "preview_ready", "Import session is ready for preview.")
        return ImportSessionCreateResponse(import_session_id=session.id, status=session.status, source_type=session.source_type)

    def _discard_folder_session(self, import_session_id: str) -> None:
        session = self.import_sessions.pop(import_session_id, None)
        if session is not None:
            self._cleanup_session_root(settings.upload_storage_dir / "import_sessions" / session.id)

    def create_github_import_session(self, url: str, name: str | None, branch: str | None = None) -> ImportSessionCreateResponse:
        session, clone_url, validated_branch = self._new_github_import_session(url, name, branch)
        self._prepare_github_import_session(session, clone_url, validated_branch, propagate_error=True)
        return ImportSessionCreateResponse(import_session_id=session.id, status=session.status, source_type=session.source_type)

    def start_github_import_session(self, url: str, name: str | None, branch: str | None = None) -> ImportSessionCreateResponse:
        """Acknowledge UI acquisition immediately and prepare the preview off-request."""

        session, clone_url, validated_branch = self._new_github_import_session(url, name, branch)
        Thread(
            target=self._prepare_github_import_session,
            args=(session, clone_url, validated_branch),
            name=f"github-import-{session.id}",
            daemon=True,
        ).start()
        return ImportSessionCreateResponse(import_session_id=session.id, status=session.status, source_type=session.source_type)

    def _new_github_import_session(
        self,
        url: str,
        name: str | None,
        branch: str | None,
    ) -> tuple[ImportSessionRecord, str, str | None]:
        clone_url, source_label, suggested_name = self._validate_github_url(url)
        validated_branch = self._validate_git_ref(branch)
        session_id = f"import_{uuid4().hex[:10]}"
        activity_logs: list[dict[str, str | dict[str, str]]] = []
        self._append_activity_log(
            activity_logs,
            "github_received",
            "GitHub import request received.",
            source_label=source_label,
            branch=validated_branch or "default",
        )
        session_root = settings.upload_storage_dir / "import_sessions" / session_id
        source_dir = session_root / "source"
        session = ImportSessionRecord(
            id=session_id,
            name=name or suggested_name,
            source_type="github_url",
            source_uri=clone_url,
            source_label=source_label,
            source_path=source_dir,
            status="preparing",
            created_at=utc_now(),
            activity_logs=activity_logs,
        )
        self.import_sessions[session.id] = session
        return session, clone_url, validated_branch

    def _prepare_github_import_session(
        self,
        session: ImportSessionRecord,
        clone_url: str,
        validated_branch: str | None,
        propagate_error: bool = False,
    ) -> None:
        session_root = session.source_path.parent
        session_root.mkdir(parents=True, exist_ok=True)
        session.status = "cloning"
        self._log_session(session, "github_clone_started", "Cloning the repository from GitHub.")
        try:
            self._clone_github_repository(clone_url, session.source_path, validated_branch)
            if session.status == "cancelled":
                self._cleanup_session_root(session_root)
                return
            session.status = "validating"
            self._log_session(session, "github_metadata_cleanup", "Removing Git metadata from the source snapshot.")
            self._remove_git_metadata(session.source_path)
            if session.status == "cancelled":
                self._cleanup_session_root(session_root)
                return
            self._log_session(session, "github_tree_validation", "Checking repository paths and acquisition limits.")
            self._validate_import_tree(session.source_path)
            if session.status == "cancelled":
                self._cleanup_session_root(session_root)
                return
        except FileNotFoundError as exc:
            error = DomainError("GIT_NOT_AVAILABLE", "Git executable is not available on this machine.", 500)
        except subprocess.TimeoutExpired as exc:
            error = DomainError("GITHUB_IMPORT_TIMEOUT", "GitHub import timed out before preview could be prepared.", 504)
        except subprocess.CalledProcessError as exc:
            error = DomainError("GITHUB_IMPORT_FAILED", "Could not clone the GitHub repository for preview.", 400)
        except Exception as exc:
            error = exc if isinstance(exc, DomainError) else DomainError(
                "GITHUB_IMPORT_FAILED", "Could not prepare the GitHub repository preview.", 500
            )
        else:
            session.status = "preview_ready"
            self._log_session(session, "github_cloned", "GitHub repository is ready for preview.")
            return

        if session.status == "cancelled":
            self._cleanup_session_root(session_root)
            return
        self._cleanup_session_root(session_root)
        session.status = "failed"
        session.error_code = error.code
        session.error_message = error.message
        self._log_session(session, "github_failed", error.message, level="error", error_code=error.code)
        if propagate_error:
            raise error

    def get_import_session_status(self, import_session_id: str) -> ImportSessionStatusResponse:
        session = self.import_sessions.get(import_session_id)
        if session is None:
            raise DomainError("IMPORT_SESSION_NOT_FOUND", "Import session not found.", 404, {"import_session_id": import_session_id})
        latest = session.activity_logs[-1] if session.activity_logs else {}
        return ImportSessionStatusResponse(
            import_session_id=session.id,
            status=session.status,
            stage=str(latest.get("stage") or session.status),
            message=str(latest.get("message") or "Preparing import session."),
            activity_logs=session.activity_logs,
            error_code=session.error_code,
            error_message=session.error_message,
        )

    def get_import_preview(self, import_session_id: str) -> ImportPreviewResponse:
        session = self._get_import_session(import_session_id)
        if session.status != "preview_ready" and session.status != "confirmed":
            if session.status == "failed":
                raise DomainError(
                    session.error_code or "GITHUB_IMPORT_FAILED",
                    session.error_message or "Could not prepare the GitHub repository preview.",
                    400,
                )
            raise DomainError(
                "IMPORT_SESSION_NOT_READY",
                "Import preview is still being prepared.",
                409,
                {"retryable": True, "status": session.status},
            )
        if session.preview_response is not None:
            payload = session.preview_response.model_dump()
            payload["possible_duplicates"] = self._possible_import_duplicates(session)
            payload["activity_logs"] = session.activity_logs
            payload["status"] = session.status
            return ImportPreviewResponse.model_validate(payload)
        self._log_session(session, "preview_scan_started", "Preview scan started.")

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
        file_statistics = self._import_file_statistics(preview_repository, scan_result)
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
        session.preview_project_fingerprint = self._project_fingerprint(scan_result.files)
        self._log_session(
            session,
            "preview_scan_completed",
            "Preview scan completed.",
            total_files=file_statistics.total_files,
            supported_files=file_statistics.supported_files,
            skipped_files=file_statistics.skipped_files,
            repository_size_bytes=scan_result.total_size_bytes,
        )
        preview_response = ImportPreviewResponse(
            import_session_id=session.id,
            status=session.status,
            project_summary=ImportProjectSummaryDTO(
                suggested_name=session.name,
                source_type=session.source_type,
                repository_size_bytes=scan_result.total_size_bytes,
                estimated_index_time_seconds=self._estimate_index_time_seconds(scan_result, file_statistics),
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
            activity_logs=session.activity_logs,
        )
        session.preview_response = preview_response
        return preview_response

    def confirm_import_session(
        self,
        import_session_id: str,
        name: str | None,
        start_indexing: bool,
        duplicate_action: str = "import_as_new",
        run_in_background: bool = False,
    ) -> ImportConfirmResponse:
        session = self._get_import_session(import_session_id)
        if duplicate_action == "cancel":
            self._log_session(session, "cancelled", "Import session cancelled by duplicate action.", level="warning")
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
        self._log_session(session, "confirm_started", "Import confirmation started.", repository_id=repository_id)
        original_source_path = session.source_path
        moved_source = False
        try:
            shutil.move(str(original_source_path), str(source_dir))
            moved_source = True
            repository = RepositoryState(
                id=repository_id,
                name=name or session.name,
                source_type=session.source_type,
                source_uri=session.source_uri,
                source_label=session.source_label,
                source_path=source_dir,
                project_fingerprint=session.preview_project_fingerprint,
            )
            self.repositories.create_repository(repository)
        except Exception:
            if moved_source:
                self._rollback_confirmed_source(source_dir, original_source_path)
            raise
        session.status = "confirmed"
        session.confirmed_repository_id = repository.id
        self._log_session(session, "repository_created", "Repository record created.", repository_id=repository.id)

        indexing_job_id = None
        if start_indexing:
            if run_in_background:
                result = self.indexing.start_indexing_background(repository.id, force_reindex=True)
            else:
                result = self.indexing.start_indexing(repository.id, force_reindex=True)
            indexing_job_id = result.indexing_job_id
            self._log_session(
                session,
                "indexing_started",
                "Indexing job started.",
                repository_id=repository.id,
                indexing_job_id=indexing_job_id,
            )
        return ImportConfirmResponse(
            repository_id=repository.id,
            indexing_job_id=indexing_job_id,
            status=repository.status,
            index_version=repository.current_index_version,
        )

    def cancel_import_session(self, import_session_id: str) -> ImportCancelResponse:
        session = self._get_import_session(import_session_id)
        acquisition_running = session.source_type == "github_url" and session.status in {"preparing", "cloning", "validating"}
        session.status = "cancelled"
        self._log_session(session, "cancelled", "Import session cancelled.")
        if acquisition_running:
            return ImportCancelResponse(cancelled=True, import_session_id=import_session_id)
        session_root = settings.upload_storage_dir / "import_sessions" / session.id
        if session_root.exists() and self.archive.is_relative_to(session_root.resolve(), settings.upload_storage_dir.resolve()):
            shutil.rmtree(session_root)
        self.import_sessions.pop(session.id, None)
        return ImportCancelResponse(cancelled=True, import_session_id=import_session_id)

    def _log_session(
        self,
        session: ImportSessionRecord,
        stage: str,
        message: str,
        level: str = "info",
        **details: str | int,
    ) -> None:
        self._append_activity_log(session.activity_logs, stage, message, level, **details)
        if session.preview_response is not None:
            payload = session.preview_response.model_dump()
            payload["activity_logs"] = session.activity_logs
            payload["status"] = session.status
            session.preview_response = ImportPreviewResponse.model_validate(payload)

    def _append_activity_log(
        self,
        logs: list[dict[str, str | dict[str, str]]],
        stage: str,
        message: str,
        level: str = "info",
        **details: str | int,
    ) -> None:
        logs.append(
            {
                "timestamp": utc_now(),
                "level": level,
                "stage": stage,
                "message": message,
                "details": {key: str(value) for key, value in details.items() if value is not None},
            }
        )

    def _get_import_session(self, import_session_id: str) -> ImportSessionRecord:
        session = self.import_sessions.get(import_session_id)
        if session is None:
            raise DomainError("IMPORT_SESSION_NOT_FOUND", "Import session not found.", 404, {"import_session_id": import_session_id})
        if session.status in {"cancelled", "expired", "failed"}:
            raise DomainError("IMPORT_SESSION_NOT_AVAILABLE", "Import session is not available.", 409, {"import_session_id": import_session_id})
        return session

    def _import_file_statistics(self, repository: RepositoryState, scan_result: ScanResult) -> ImportFileStatisticsDTO:
        language_files = scan_result.language_files or {}
        return ImportFileStatisticsDTO(
            total_files=scan_result.total_files,
            supported_files=len(repository.files),
            skipped_files=max(0, scan_result.total_files - len(repository.files)),
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

    def _rollback_confirmed_source(self, source_dir: Path, original_source_path: Path) -> None:
        try:
            if source_dir.exists() and not original_source_path.exists():
                original_source_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_dir), str(original_source_path))
            elif source_dir.exists() and self.archive.is_relative_to(source_dir.resolve(), settings.repository_storage_dir.resolve()):
                shutil.rmtree(source_dir)
        except OSError:
            return

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
            repository_fingerprint = repository.project_fingerprint or self._project_fingerprint(repository.files)
            if session.preview_project_fingerprint and repository_fingerprint == session.preview_project_fingerprint:
                duplicates.append(
                    ImportDuplicateCandidateDTO(
                        repository_id=repository.id,
                        name=repository.name,
                        match_reason="same_fingerprint",
                    )
                )
            elif repository.name.lower() == session_name:
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

    def _estimate_index_time_seconds(self, scan_result: ScanResult, file_statistics: ImportFileStatisticsDTO) -> int:
        file_cost = file_statistics.supported_files * 0.03
        size_cost = (scan_result.supported_size_bytes / 1_000_000) * 0.15
        parser_cost = (
            file_statistics.python_files * 0.02
            + file_statistics.typescript_files * 0.04
            + file_statistics.javascript_files * 0.03
            + file_statistics.markdown_files * 0.01
        )
        return max(1, math.ceil(file_cost + size_cost + parser_cost))

    def _project_fingerprint(self, files: list[FileRecord]) -> str | None:
        if not files:
            return None
        digest = hashlib.sha256()
        for file in sorted(files, key=lambda item: item.path):
            digest.update(file.path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(file.size_bytes).encode("ascii"))
            digest.update(b"\0")
            digest.update(file.content_hash.encode("ascii"))
            digest.update(b"\n")
        return digest.hexdigest()

    def _validate_github_url(self, raw_url: str) -> tuple[str, str, str]:
        parsed = urlparse(raw_url.strip())
        try:
            port = parsed.port
        except ValueError as exc:
            raise DomainError("INVALID_GITHUB_URL", "Only public HTTPS GitHub repository URLs are supported.", 400) from exc
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"github.com", "www.github.com"}
            or parsed.username is not None
            or parsed.password is not None
            or port is not None
            or parsed.query
            or parsed.fragment
            or parsed.params
        ):
            raise DomainError("INVALID_GITHUB_URL", "Only public HTTPS GitHub repository URLs are supported.", 400)
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) != 2:
            raise DomainError("INVALID_GITHUB_URL", "GitHub URL must include owner and repository name.", 400)
        owner = parts[0]
        repository = parts[1].removesuffix(".git")
        if (
            not _GITHUB_OWNER.fullmatch(owner)
            or not _GITHUB_REPOSITORY.fullmatch(repository)
            or repository in {".", ".."}
        ):
            raise DomainError("INVALID_GITHUB_URL", "GitHub URL contains an invalid owner or repository name.", 400)
        source_label = f"{owner}/{repository}"
        return f"https://github.com/{source_label}.git", source_label, repository

    def _validate_git_ref(self, branch: str | None) -> str | None:
        if branch is None:
            return None
        candidate = branch.strip()
        forbidden = ("..", "@{", "\\", " ", "~", "^", ":", "?", "*", "[")
        if (
            not candidate
            or len(candidate) > 255
            or candidate.startswith(("-", ".", "/"))
            or candidate.endswith((".", "/", ".lock"))
            or "//" in candidate
            or any(token in candidate for token in forbidden)
            or any(ord(character) < 32 or ord(character) == 127 for character in candidate)
        ):
            raise DomainError("INVALID_GIT_REF", "Git reference is invalid.", 400)
        return candidate

    def _clone_github_repository(self, clone_url: str, source_dir: Path, branch: str | None = None) -> None:
        sandbox_home = source_dir.parent / ".git-home"
        disabled_hooks = source_dir.parent / ".disabled-git-hooks"
        sandbox_home.mkdir(parents=True, exist_ok=True)
        disabled_hooks.mkdir(parents=True, exist_ok=True)
        command = [
            "git",
            "-c",
            "protocol.allow=never",
            "-c",
            "protocol.https.allow=always",
            "-c",
            "http.followRedirects=false",
            "-c",
            "credential.helper=",
            "-c",
            f"core.hooksPath={disabled_hooks}",
            "-c",
            "submodule.recurse=false",
            "-c",
            "filter.lfs.smudge=",
            "-c",
            "filter.lfs.required=false",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--no-tags",
            "--no-recurse-submodules",
        ]
        if branch:
            command.extend(["--branch", branch])
        command.extend([clone_url, str(source_dir)])
        inherited_environment = {
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "LANG",
            "LC_ALL",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "HTTPS_PROXY",
            "NO_PROXY",
        }
        environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in inherited_environment
        }
        environment.update(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "GCM_INTERACTIVE": "Never",
                "GIT_ALLOW_PROTOCOL": "https",
                "GIT_LFS_SKIP_SMUDGE": "1",
                "GIT_PROTOCOL_FROM_USER": "0",
                "HOME": str(sandbox_home),
                "USERPROFILE": str(sandbox_home),
                "XDG_CONFIG_HOME": str(sandbox_home),
            }
        )
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=settings.git_clone_timeout_seconds,
                env=environment,
            )
        finally:
            shutil.rmtree(sandbox_home, ignore_errors=True)
            shutil.rmtree(disabled_hooks, ignore_errors=True)

    def _remove_git_metadata(self, source_dir: Path) -> None:
        git_path = source_dir / ".git"
        if git_path.is_symlink():
            raise DomainError("GIT_METADATA_INVALID", "Cloned repository contains invalid Git metadata.", 400)
        if git_path.is_dir():
            self._remove_tree(git_path)
        elif git_path.exists():
            git_path.unlink()

    def _validate_import_tree(self, source_dir: Path) -> None:
        source_root = source_dir.resolve()
        quota = ImportQuota.configured()
        seen_paths: set[str] = set()
        for current_root, directory_names, file_names in os.walk(source_root, followlinks=False):
            current_path = Path(current_root)
            for name in [*directory_names, *file_names]:
                candidate = current_path / name
                relative_path = normalized_relative_path(candidate.relative_to(source_root).as_posix())
                ensure_unique_path(relative_path, seen_paths)
                metadata = candidate.lstat()
                if stat.S_ISLNK(metadata.st_mode):
                    raise DomainError("IMPORT_LINK_NOT_ALLOWED", "Imported repository links are not allowed.", 400)
                if name in file_names:
                    if not stat.S_ISREG(metadata.st_mode):
                        raise DomainError("IMPORT_SPECIAL_FILE_NOT_ALLOWED", "Imported repository special files are not allowed.", 400)
                    # Acquisition remains bounded by file count and aggregate bytes. The scanner
                    # applies the per-file content limit and records oversized files as skipped.
                    quota.add_file(metadata.st_size, enforce_file_size=False)

    def _cleanup_session_root(self, session_root: Path) -> None:
        upload_root = settings.upload_storage_dir.resolve()
        resolved_session = session_root.resolve()
        if (
            resolved_session != upload_root
            and self.archive.is_relative_to(resolved_session, upload_root)
            and resolved_session.exists()
        ):
            self._remove_tree(resolved_session, ignore_errors=True)

    @staticmethod
    def _remove_tree(path: Path, *, ignore_errors: bool = False) -> None:
        """Remove a bounded tree, including read-only files created by Git on Windows."""

        def make_writable_and_retry(function, denied_path, error_info) -> None:
            error = error_info[1]
            if not isinstance(error, PermissionError):
                raise error
            os.chmod(denied_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            function(denied_path)

        try:
            shutil.rmtree(path, onerror=make_writable_and_retry)
        except OSError:
            if not ignore_errors:
                raise
