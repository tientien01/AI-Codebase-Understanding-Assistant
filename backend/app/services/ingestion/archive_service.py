from __future__ import annotations

import stat
import zipfile
from pathlib import Path

from app.core.config import settings
from app.core.errors import DomainError
from app.services.ingestion.import_policy import ImportQuota, ensure_unique_path, normalized_relative_path
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
        extracted_files = 0
        total_written = 0
        max_total_bytes = settings.max_extracted_size_mb * 1024 * 1024
        max_file_bytes = settings.max_file_size_mb * 1024 * 1024
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.infolist()
            self.validate_zip_plan(members, target_root)

            for member in members:
                relative_path = self.safe_zip_member_path(member, target_root, skipped_records, security_records)
                if member.is_dir() or relative_path is None:
                    continue
                if relative_path.suffix.lower() in self.nested_archive_extensions:
                    self.record_skipped(skipped_records, relative_path.as_posix(), "nested_archive", relative_path.suffix.lower())
                    continue
                destination = target_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                member_written = 0
                with archive.open(member) as source, destination.open("xb") as target:
                    while chunk := source.read(settings.upload_chunk_size_mb * 1024 * 1024):
                        member_written += len(chunk)
                        total_written += len(chunk)
                        if member_written > max_file_bytes:
                            raise DomainError(
                                "IMPORT_FILE_TOO_LARGE",
                                "Archive contains a file larger than the configured limit.",
                                413,
                            )
                        if total_written > max_total_bytes:
                            raise DomainError(
                                "REPOSITORY_TOO_LARGE",
                                "Archive content is larger than the configured limit.",
                                413,
                            )
                        target.write(chunk)
                extracted_files += 1
        return extracted_files

    def validate_zip_plan(self, members: list[zipfile.ZipInfo], target_root: Path) -> None:
        seen_paths: set[str] = set()
        quota = ImportQuota.configured()
        for member in members:
            relative_path = self._validated_member_path(member, target_root)
            self._validate_member_type(member)
            try:
                ensure_unique_path(relative_path, seen_paths)
            except DomainError:
                raise DomainError("DUPLICATE_ARCHIVE_PATH", "Zip archive contains duplicate paths after normalization.", 400)
            if member.is_dir():
                continue
            quota.add_file(member.file_size)
            if member.file_size > 0 and (
                member.compress_size <= 0
                or member.file_size / member.compress_size > settings.max_archive_compression_ratio
            ):
                raise DomainError("ZIP_BOMB_RISK", "Zip archive has an unsafe compression ratio.", 400)

    def safe_zip_member_path(
        self,
        member: zipfile.ZipInfo,
        target_root: Path,
        skipped_records: list[dict[str, str | None]] | None = None,
        security_records: list[dict[str, str]] | None = None,
    ) -> Path | None:
        relative_path = self._validated_member_path(member, target_root)
        if member.is_dir():
            return None
        ignored_names = {item.casefold() for item in IGNORE_DIRS}
        ignored_part = next((part for part in relative_path.parts if part.casefold() in ignored_names), None)
        if ignored_part:
            self.record_skipped(skipped_records, relative_path.as_posix(), "ignored_folder", ignored_part)
            return None
        if is_secret_file(relative_path.name):
            self.record_skipped(skipped_records, relative_path.as_posix(), "secret_file", relative_path.name)
            if security_records is not None:
                security_records.append({"file_path": relative_path.as_posix(), "risk_type": "secret_file", "action": "skipped"})
            return None
        if relative_path.suffix.lower() in self.nested_archive_extensions:
            self.record_skipped(skipped_records, relative_path.as_posix(), "nested_archive", relative_path.suffix.lower())
            return None
        if not is_supported_file(relative_path):
            self.record_skipped(skipped_records, relative_path.as_posix(), "unsupported_file_type", relative_path.suffix.lower() or relative_path.name)
            return None
        return relative_path

    def _validated_member_path(self, member: zipfile.ZipInfo, target_root: Path) -> Path:
        try:
            relative_path = normalized_relative_path(member.filename.rstrip("/"))
        except DomainError as exc:
            code = "ARCHIVE_PATH_TOO_DEEP" if exc.code == "IMPORT_PATH_TOO_DEEP" else "ARCHIVE_PATH_TRAVERSAL"
            raise DomainError(code, "Zip archive contains an unsafe path.", 400) from exc
        destination = (target_root / relative_path).resolve()
        if not self.is_relative_to(destination, target_root):
            raise DomainError("ARCHIVE_PATH_TRAVERSAL", "Zip archive contains unsafe paths.", 400)
        return relative_path

    def _validate_member_type(self, member: zipfile.ZipInfo) -> None:
        unix_mode = member.external_attr >> 16
        file_type = stat.S_IFMT(unix_mode)
        if stat.S_ISLNK(unix_mode):
            raise DomainError("ARCHIVE_LINK_NOT_ALLOWED", "Archive links are not allowed.", 400)
        if file_type and not (stat.S_ISREG(unix_mode) or stat.S_ISDIR(unix_mode)):
            raise DomainError("ARCHIVE_SPECIAL_FILE_NOT_ALLOWED", "Archive special files are not allowed.", 400)

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
