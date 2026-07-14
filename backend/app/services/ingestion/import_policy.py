from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.core.config import settings
from app.core.errors import DomainError


_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def normalized_relative_path(raw_path: str) -> Path:
    """Return a platform-safe relative path or reject it before any filesystem write."""

    normalized = unicodedata.normalize("NFC", raw_path.replace("\\", "/"))
    if (
        not normalized
        or normalized.startswith("/")
        or _WINDOWS_DRIVE.match(normalized)
        or _CONTROL_CHARACTERS.search(normalized)
    ):
        raise DomainError("UNSAFE_IMPORT_PATH", "Import contains an unsafe path.", 400)

    raw_parts = normalized.split("/")
    if any(part in {"", ".", ".."} or ":" in part for part in raw_parts):
        raise DomainError("UNSAFE_IMPORT_PATH", "Import contains an unsafe path.", 400)
    parts = PurePosixPath(normalized).parts
    if len(parts) > settings.max_path_depth:
        raise DomainError("IMPORT_PATH_TOO_DEEP", "Import contains a path that is too deep.", 400)
    return Path(*parts)


def path_identity(path: Path) -> str:
    """Build a deterministic identity that catches case and Unicode collisions."""

    return unicodedata.normalize("NFC", path.as_posix()).casefold()


@dataclass
class ImportQuota:
    max_files: int
    max_total_bytes: int
    max_file_bytes: int
    files: int = 0
    total_bytes: int = 0

    @classmethod
    def configured(cls) -> "ImportQuota":
        return cls(
            max_files=settings.max_zip_entries,
            max_total_bytes=settings.max_extracted_size_mb * 1024 * 1024,
            max_file_bytes=settings.max_file_size_mb * 1024 * 1024,
        )

    def add_file(self, size_bytes: int) -> None:
        if size_bytes < 0:
            raise DomainError("INVALID_IMPORT_SIZE", "Import contains an invalid file size.", 400)
        if size_bytes > self.max_file_bytes:
            raise DomainError("IMPORT_FILE_TOO_LARGE", "Import contains a file larger than the configured limit.", 413)
        if self.files + 1 > self.max_files:
            raise DomainError("TOO_MANY_FILES", "Import contains too many files.", 413)
        if self.total_bytes + size_bytes > self.max_total_bytes:
            raise DomainError("REPOSITORY_TOO_LARGE", "Import is larger than the configured limit.", 413)
        self.files += 1
        self.total_bytes += size_bytes


def ensure_unique_path(path: Path, seen_paths: set[str]) -> None:
    identity = path_identity(path)
    if identity in seen_paths:
        raise DomainError(
            "DUPLICATE_IMPORT_PATH",
            "Import contains duplicate paths after normalization.",
            400,
        )
    seen_paths.add(identity)
