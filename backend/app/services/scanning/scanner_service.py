from __future__ import annotations

from dataclasses import dataclass
import hashlib

from app.core.config import settings
from app.services.scanning.file_rules import IGNORE_DIRS, detect_file_type, detect_language, is_secret_file, is_supported_file
from app.services.index_models import FileRecord, RepositoryState


@dataclass
class SkippedFile:
    file_path: str
    reason: str
    matched_pattern: str | None = None


@dataclass
class SecurityWarning:
    file_path: str
    risk_type: str
    action: str = "skipped"


@dataclass
class ScanResult:
    files: list[FileRecord]
    skipped_files: list[SkippedFile]
    security_warnings: list[SecurityWarning]
    total_files: int = 0
    total_size_bytes: int = 0
    supported_size_bytes: int = 0
    language_files: dict[str, int] | None = None


class ScannerService:
    def __init__(self, max_file_size_mb: int | None = None) -> None:
        self.max_file_size_mb = max_file_size_mb or settings.max_file_size_mb

    def scan_files(self, repository: RepositoryState) -> list[FileRecord]:
        return self.scan_files_with_diagnostics(repository).files

    def scan_files_with_diagnostics(self, repository: RepositoryState) -> ScanResult:
        files: list[FileRecord] = []
        skipped_files: list[SkippedFile] = []
        security_warnings: list[SecurityWarning] = []
        language_files: dict[str, int] = {}
        total_files = 0
        total_size_bytes = 0
        supported_size_bytes = 0
        max_size = self.max_file_size_mb * 1024 * 1024
        for path in repository.source_path.rglob("*"):
            if not path.is_file():
                continue
            total_files += 1
            relative_parts = path.relative_to(repository.source_path).parts
            relative_path = path.relative_to(repository.source_path).as_posix()
            try:
                size = path.stat().st_size
            except OSError:
                repository.failed_files += 1
                repository.warnings.append(f"Could not stat file: {relative_path}")
                skipped_files.append(SkippedFile(relative_path, "stat_error"))
                continue
            total_size_bytes += size

            ignored_part = next((part for part in relative_parts if part in IGNORE_DIRS), None)
            if ignored_part:
                skipped_files.append(SkippedFile(relative_path, "ignored_folder", ignored_part))
                continue
            if is_secret_file(path.name):
                skipped_files.append(SkippedFile(relative_path, "secret_file", path.name))
                security_warnings.append(SecurityWarning(relative_path, "secret_file"))
                continue
            if not is_supported_file(path):
                skipped_files.append(SkippedFile(relative_path, "unsupported_file_type", path.suffix.lower() or path.name))
                continue

            if size > max_size:
                repository.warnings.append(f"Skipped large file: {relative_path}")
                skipped_files.append(SkippedFile(relative_path, "file_too_large", f">{self.max_file_size_mb}MB"))
                continue

            try:
                raw_content = path.read_bytes()
            except OSError:
                repository.failed_files += 1
                repository.warnings.append(f"Could not read file: {relative_path}")
                skipped_files.append(SkippedFile(relative_path, "read_error"))
                continue

            language = detect_language(path)
            supported_size_bytes += size
            language_files[language] = language_files.get(language, 0) + 1
            files.append(
                FileRecord(
                    path=relative_path,
                    absolute_path=path,
                    language=language,
                    file_type=detect_file_type(path),
                    size_bytes=size,
                    content_hash=hashlib.sha256(raw_content).hexdigest(),
                )
            )
        return ScanResult(
            files=files,
            skipped_files=skipped_files,
            security_warnings=security_warnings,
            total_files=total_files,
            total_size_bytes=total_size_bytes,
            supported_size_bytes=supported_size_bytes,
            language_files=language_files,
        )
