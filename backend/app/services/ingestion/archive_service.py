from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from app.core.config import settings
from app.core.errors import DomainError
from app.services.scanning.file_rules import IGNORE_DIRS, is_secret_file, is_supported_file


class ArchiveService:
    nested_archive_extensions = {".zip", ".tar", ".gz", ".tgz", ".rar", ".7z"}

    def safe_extract_zip(
        self,
        zip_path: Path,
        target_dir: Path,
        skipped_records: list[dict[str, str | None]] | None = None,
        security_records: list[dict[str, str]] | None = None,
    ) -> int:
        target_root = target_dir.resolve()
        max_uncompressed_size = settings.max_extracted_size_mb * 1024 * 1024
        max_file_size = settings.max_file_size_mb * 1024 * 1024
        extracted_files = 0
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.infolist()
            if len(members) > settings.max_zip_entries:
                raise DomainError("TOO_MANY_FILES", "Archive contains too many entries.", 413)
            self.validate_zip_plan(members, target_root, max_uncompressed_size)

            for member in members:
                relative_path = self.safe_zip_member_path(member, target_root, skipped_records, security_records)
                if member.is_dir() or relative_path is None:
                    continue
                if relative_path.suffix.lower() in self.nested_archive_extensions:
                    self.record_skipped(skipped_records, relative_path.as_posix(), "nested_archive", relative_path.suffix.lower())
                    continue
                if member.file_size > max_file_size:
                    self.record_skipped(skipped_records, relative_path.as_posix(), "file_too_large", f">{settings.max_file_size_mb}MB")
                    continue
                destination = target_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                extracted_files += 1
        return extracted_files

    def validate_zip_plan(self, members: list[zipfile.ZipInfo], target_root: Path, max_uncompressed_size: int) -> None:
        seen_paths: set[str] = set()
        total_uncompressed = 0
        for member in members:
            relative_path = self.safe_zip_member_path(member, target_root)
            if relative_path is None:
                continue
            normalized = relative_path.as_posix().lower()
            if normalized in seen_paths:
                raise DomainError("DUPLICATE_ARCHIVE_PATH", "Zip archive contains duplicate paths after normalization.", 400)
            seen_paths.add(normalized)
            total_uncompressed += member.file_size
            if total_uncompressed > max_uncompressed_size:
                raise DomainError("REPOSITORY_TOO_LARGE", "Archive content is larger than the configured limit.", 413)
            if member.compress_size > 0 and member.file_size / member.compress_size > settings.max_archive_compression_ratio:
                raise DomainError("ZIP_BOMB_RISK", "Zip archive has an unsafe compression ratio.", 400)

    def safe_zip_member_path(
        self,
        member: zipfile.ZipInfo,
        target_root: Path,
        skipped_records: list[dict[str, str | None]] | None = None,
        security_records: list[dict[str, str]] | None = None,
    ) -> Path | None:
        normalized = member.filename.replace("\\", "/").strip("/")
        if not normalized:
            return None
        relative_path = Path(normalized)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise DomainError("ARCHIVE_PATH_TRAVERSAL", "Zip archive contains unsafe paths.", 400)
        if len(relative_path.parts) > settings.max_path_depth:
            raise DomainError("ARCHIVE_PATH_TOO_DEEP", "Zip archive contains paths that are too deep.", 400)
        destination = (target_root / relative_path).resolve()
        if not self.is_relative_to(destination, target_root):
            raise DomainError("ARCHIVE_PATH_TRAVERSAL", "Zip archive contains unsafe paths.", 400)
        if member.is_dir():
            return None
        ignored_part = next((part for part in relative_path.parts if part in IGNORE_DIRS), None)
        if ignored_part:
            self.record_skipped(skipped_records, normalized, "ignored_folder", ignored_part)
            return None
        if is_secret_file(relative_path.name):
            self.record_skipped(skipped_records, normalized, "secret_file", relative_path.name)
            if security_records is not None:
                security_records.append({"file_path": normalized, "risk_type": "secret_file", "action": "skipped"})
            return None
        if relative_path.suffix.lower() in self.nested_archive_extensions:
            self.record_skipped(skipped_records, normalized, "nested_archive", relative_path.suffix.lower())
            return None
        if not is_supported_file(relative_path):
            self.record_skipped(skipped_records, normalized, "unsupported_file_type", relative_path.suffix.lower() or relative_path.name)
            return None
        return relative_path

    def record_skipped(
        self,
        skipped_records: list[dict[str, str | None]] | None,
        file_path: str,
        reason: str,
        matched_pattern: str | None = None,
    ) -> None:
        if skipped_records is None:
            return
        skipped_records.append({"file_path": file_path, "reason": reason, "matched_pattern": matched_pattern})

    def is_relative_to(self, path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
        except ValueError:
            return False
        return True
