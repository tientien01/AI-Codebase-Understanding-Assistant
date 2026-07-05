from __future__ import annotations

from pathlib import Path

from app.services.ingestion.archive_service import ArchiveService
from app.services.scanning.file_rules import IGNORE_DIRS, is_secret_file, is_supported_file


class UploadService:
    def __init__(self, archive: ArchiveService | None = None) -> None:
        self.archive = archive or ArchiveService()

    def safe_upload_relative_path(
        self,
        raw_path: str,
        skipped_records: list[dict[str, str | None]] | None = None,
        security_records: list[dict[str, str]] | None = None,
    ) -> Path | None:
        normalized = raw_path.replace("\\", "/").strip("/")
        if not normalized:
            return None
        path = Path(normalized)
        if path.is_absolute() or ".." in path.parts:
            self.archive.record_skipped(skipped_records, normalized, "unsafe_path")
            return None
        ignored_part = next((part for part in path.parts if part in IGNORE_DIRS), None)
        if ignored_part:
            self.archive.record_skipped(skipped_records, normalized, "ignored_folder", ignored_part)
            return None
        if is_secret_file(path.name):
            self.archive.record_skipped(skipped_records, normalized, "secret_file", path.name)
            if security_records is not None:
                security_records.append({"file_path": normalized, "risk_type": "secret_file", "action": "skipped"})
            return None
        if not is_supported_file(path):
            self.archive.record_skipped(skipped_records, normalized, "unsupported_file_type", path.suffix.lower() or path.name)
            return None
        return path

    def is_relative_to(self, path: Path, parent: Path) -> bool:
        return self.archive.is_relative_to(path, parent)
