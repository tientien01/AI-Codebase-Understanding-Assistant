from __future__ import annotations

from app.services.chunking_service import ChunkingService
from app.services.index_models import FileRecord, RepositoryState
from app.services.parsing.base import LanguageParser


class SourceFallbackParser(LanguageParser):
    def __init__(self, chunking: ChunkingService) -> None:
        self.chunking = chunking

    def parse(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        chunk_type = self._chunk_type(file_record)
        self.chunking.add_chunk(
            repository,
            file_record.path,
            chunk_type,
            text,
            1,
            max(1, len(text.splitlines())),
        )

    def _chunk_type(self, file_record: FileRecord) -> str:
        if file_record.language == "markdown":
            return "doc_section"
        if file_record.file_type == "config" or file_record.language == "docker":
            return "config_section"
        return "file_summary"
