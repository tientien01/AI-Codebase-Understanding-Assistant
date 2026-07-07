from __future__ import annotations

from app.services.index_models import ChunkRecord, RepositoryState
from app.services.code_analysis.stable_ids import stable_chunk_id
from app.services.text_utils import content_hash


class ChunkingService:
    def add_chunk(
        self,
        repository: RepositoryState,
        file_path: str,
        chunk_type: str,
        content: str,
        start_line: int,
        end_line: int,
        symbol_name: str | None = None,
    ) -> None:
        normalized = content.strip()
        if not normalized:
            return
        digest = content_hash(f"{file_path}:{start_line}:{end_line}:{normalized}")
        anchor_key = symbol_name or f"{start_line}:{end_line}"
        repository.chunks.append(
            ChunkRecord(
                id=stable_chunk_id(repository.id, file_path, chunk_type, anchor_key, digest),
                file_path=file_path,
                chunk_type=chunk_type,
                content=normalized,
                start_line=start_line,
                end_line=end_line,
                symbol_name=symbol_name,
                content_hash=digest,
            )
        )

    def create_file_summary_chunks(self, repository: RepositoryState) -> None:
        existing = {(chunk.file_path, chunk.chunk_type) for chunk in repository.chunks}
        for file_record in repository.files:
            if (file_record.path, "file_summary") in existing:
                continue
            summary = f"{file_record.path} ({file_record.language}, {file_record.file_type})"
            self.add_chunk(repository, file_record.path, "file_summary", summary, 1, 1)
