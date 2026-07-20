from __future__ import annotations

import re

from app.services.chunking_service import ChunkingService
from app.services.code_analysis.stable_ids import stable_symbol_id, unique_definition_id
from app.services.index_models import FileRecord, RepositoryState, SymbolRecord
from app.services.parsing.base import LanguageParser


GO_FUNCTION_PATTERN = re.compile(r"^\s*func\s+(?:\([^)]+\)\s*)?([A-Za-z_]\w*)\s*\(")


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
        self._extract_fallback_symbols(repository, file_record, text)

    def _chunk_type(self, file_record: FileRecord) -> str:
        if file_record.language == "markdown":
            return "doc_section"
        if file_record.file_type == "config" or file_record.language == "docker":
            return "config_section"
        return "file_summary"

    def _extract_fallback_symbols(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        if file_record.language != "go":
            return
        lines = text.splitlines()
        for index, line in enumerate(lines, start=1):
            match = GO_FUNCTION_PATTERN.match(line)
            if not match:
                continue
            name = match.group(1)
            end_line = self._block_end_line(lines, index)
            repository.symbols.append(
                SymbolRecord(
                    id=unique_definition_id(
                        stable_symbol_id(repository.id, file_record.path, name, "function"),
                        (item.id for item in repository.symbols),
                    ),
                    name=name,
                    symbol_type="function",
                    file_path=file_record.path,
                    start_line=index,
                    end_line=end_line,
                    signature=line.strip(),
                )
            )
            self.chunking.add_chunk(
                repository,
                file_record.path,
                "function",
                "\n".join(lines[index - 1 : end_line]),
                index,
                end_line,
                name,
            )

    def _block_end_line(self, lines: list[str], start_line: int) -> int:
        depth = 0
        seen_open = False
        for index in range(start_line, len(lines) + 1):
            line = lines[index - 1]
            depth += line.count("{")
            if "{" in line:
                seen_open = True
            depth -= line.count("}")
            if seen_open and depth <= 0:
                return index
        return min(len(lines), start_line + 12)
