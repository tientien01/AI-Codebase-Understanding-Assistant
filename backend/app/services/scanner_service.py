from __future__ import annotations

import hashlib

from app.core.config import settings
from app.services.file_rules import IGNORE_DIRS, detect_file_type, detect_language, is_secret_file, is_supported_file
from app.services.index_models import FileRecord, RepositoryState


class ScannerService:
    def __init__(self, max_file_size_mb: int | None = None) -> None:
        self.max_file_size_mb = max_file_size_mb or settings.max_file_size_mb

    def scan_files(self, repository: RepositoryState) -> list[FileRecord]:
        files: list[FileRecord] = []
        max_size = self.max_file_size_mb * 1024 * 1024
        for path in repository.source_path.rglob("*"):
            if not path.is_file():
                continue
            relative_parts = path.relative_to(repository.source_path).parts
            if any(part in IGNORE_DIRS for part in relative_parts):
                continue
            if is_secret_file(path.name):
                continue
            if not is_supported_file(path):
                continue

            relative_path = path.relative_to(repository.source_path).as_posix()
            size = path.stat().st_size
            if size > max_size:
                repository.warnings.append(f"Skipped large file: {relative_path}")
                continue

            try:
                raw_content = path.read_bytes()
            except OSError:
                repository.failed_files += 1
                repository.warnings.append(f"Could not read file: {relative_path}")
                continue

            files.append(
                FileRecord(
                    path=relative_path,
                    absolute_path=path,
                    language=detect_language(path),
                    file_type=detect_file_type(path),
                    size_bytes=size,
                    content_hash=hashlib.sha256(raw_content).hexdigest(),
                )
            )
        return files
