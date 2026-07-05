from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import DomainError


class StreamingUploadService:
    def __init__(self, chunk_size_mb: int | None = None) -> None:
        self.chunk_size_bytes = (chunk_size_mb or settings.upload_chunk_size_mb) * 1024 * 1024

    async def save_upload(self, file: UploadFile, target_path: Path, max_size_bytes: int) -> int:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        total_bytes = 0
        try:
            with target_path.open("wb") as output:
                while True:
                    chunk = await file.read(self.chunk_size_bytes)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_size_bytes:
                        raise DomainError("UPLOAD_TOO_LARGE", "Uploaded file is larger than the configured limit.", 413)
                    output.write(chunk)
        except Exception:
            target_path.unlink(missing_ok=True)
            raise
        return total_bytes
