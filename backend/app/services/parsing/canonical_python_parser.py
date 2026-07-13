from __future__ import annotations

from app.services.chunking_service import ChunkingService
from app.services.code_analysis.pipeline import CodeAnalysisPipeline
from app.services.index_models import FileRecord, RepositoryState
from app.services.parsing.base import LanguageParser


class CanonicalPythonParser(LanguageParser):
    """Compatibility projection from canonical Python IR to RepositoryState."""

    def __init__(self, chunking: ChunkingService) -> None:
        self.chunking = chunking
        self.code_analysis = CodeAnalysisPipeline(chunking)

    def parse(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        if self.code_analysis.parse_python(repository, file_record, text):
            return

        repository.failed_files += 1
        file_record.parse_status = "failed"
        repository.warnings.append(f"Python parse error: {file_record.path}")
        self.chunking.add_chunk(
            repository,
            file_record.path,
            "file_summary",
            text,
            1,
            max(1, len(text.splitlines())),
        )
