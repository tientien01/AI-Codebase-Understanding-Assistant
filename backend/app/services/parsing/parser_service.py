from __future__ import annotations

from collections.abc import Callable

from app.services.chunking_service import ChunkingService
from app.services.index_models import RepositoryState
from app.services.language_registry import LANGUAGE_DEFINITIONS, SOURCE_LANGUAGES
from app.services.parsing.base import LanguageParser
from app.services.parsing.javascript_parser import JavaScriptTypeScriptParser
from app.services.parsing.canonical_python_parser import CanonicalPythonParser
from app.services.parsing.source_fallback_parser import SourceFallbackParser
from app.services.parsing.tree_sitter_parser import TreeSitterLanguageParser
from app.services.text_utils import read_text


class ParserService:
    def __init__(self, chunking: ChunkingService | None = None) -> None:
        self.chunking = chunking or ChunkingService()
        self.fallback_parser = SourceFallbackParser(self.chunking)
        self.parsers = self._build_parser_registry()

    def parse_files(self, repository: RepositoryState, before_file: Callable[[], None] | None = None, after_file: Callable[[], None] | None = None) -> None:
        for file_record in repository.files:
            if before_file:
                before_file()
            try:
                text = read_text(file_record.absolute_path)
            except OSError:
                repository.failed_files += 1
                file_record.parse_status = "failed"
                repository.warnings.append(f"Read error: {file_record.path}")
                repository.failed_file_records.append(
                    {
                        "file_path": file_record.path,
                        "stage": "reading_files",
                        "error_code": "READ_ERROR",
                        "message": "Could not read file safely.",
                        "line": None,
                    }
                )
                if after_file:
                    after_file()
                continue

            parser = self.parsers.get(file_record.language, self.fallback_parser)
            before_chunks = len(repository.chunks)
            try:
                parser.parse(repository, file_record, text)
            except Exception as exc:
                repository.failed_files += 1
                file_record.parse_status = "failed"
                message = f"{type(exc).__name__}: {exc}"
                repository.warnings.append(f"Parser error: {file_record.path}: {message}")
                repository.failed_file_records.append(
                    {
                        "file_path": file_record.path,
                        "stage": "parsing_files",
                        "error_code": "PARSER_EXCEPTION",
                        "message": message,
                        "line": None,
                    }
                )
                repository.parse_diagnostics.append(
                    {
                        "file_path": file_record.path,
                        "language": file_record.language,
                        "parser": parser.__class__.__name__,
                        "stage": "parse",
                        "severity": "error",
                        "message": message,
                        "line": None,
                    }
                )
            if file_record.language in SOURCE_LANGUAGES and len(repository.chunks) == before_chunks:
                self.fallback_parser.parse(repository, file_record, text)
            if after_file:
                after_file()

    def _build_parser_registry(self) -> dict[str, LanguageParser]:
        definitions = {definition.language: definition for definition in LANGUAGE_DEFINITIONS}
        parsers: dict[str, LanguageParser] = {
            "python": CanonicalPythonParser(self.chunking),
            "markdown": self.fallback_parser,
            "config": self.fallback_parser,
            "docker": self.fallback_parser,
        }

        for language in ("javascript", "typescript"):
            definition = definitions[language]
            parsers[language] = JavaScriptTypeScriptParser(
                self.chunking,
                TreeSitterLanguageParser(definition),
            )

        for definition in LANGUAGE_DEFINITIONS:
            if definition.language in parsers or definition.language not in SOURCE_LANGUAGES:
                continue
            parsers[definition.language] = TreeSitterLanguageParser(definition)
        return parsers
