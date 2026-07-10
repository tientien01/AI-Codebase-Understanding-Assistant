from __future__ import annotations

import re

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO
from app.services.chunking_service import ChunkingService
from app.services.code_analysis.stable_ids import stable_node_id, stable_symbol_id
from app.services.index_models import FileRecord, RepositoryState, SymbolRecord
from app.services.parsing.base import LanguageParser
from app.services.parsing.tree_sitter_parser import TreeSitterLanguageParser
from app.services.text_utils import node_id


class JavaScriptTypeScriptParser(LanguageParser):
    def __init__(self, chunking: ChunkingService, tree_sitter: TreeSitterLanguageParser | None = None) -> None:
        self.chunking = chunking
        self.tree_sitter = tree_sitter
        self.function_pattern = re.compile(r"(?:function\s+([A-Z_a-z][\w]*)|const\s+([A-Z_a-z][\w]*)\s*=\s*(?:async\s*)?\(?[^=]*\)?\s*=>)")
        self.api_pattern = re.compile(r"(axios\.(get|post|put|delete|patch)|fetch)\s*\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
        self.import_pattern = re.compile(r"^\s*import\s+(?:.+?\s+from\s+)?['\"]([^'\"]+)['\"]")

    def parse(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        existing_symbols = len(repository.symbols)
        if self.tree_sitter is not None:
            self.tree_sitter.parse(repository, file_record, text)
        if len(repository.symbols) == existing_symbols:
            self._parse_symbols_with_regex(repository, file_record, text)
        self._parse_imports_and_api_calls(repository, file_record, text)

    def _parse_symbols_with_regex(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        lines = text.splitlines()
        for index, line in enumerate(lines, start=1):
            function_match = self.function_pattern.search(line)
            if not function_match:
                continue
            name = function_match.group(1) or function_match.group(2)
            symbol_type = "component" if name[:1].isupper() else "function"
            repository.symbols.append(
                SymbolRecord(
                    id=stable_symbol_id(repository.id, file_record.path, name, symbol_type),
                    name=name,
                    symbol_type=symbol_type,
                    file_path=file_record.path,
                    start_line=index,
                    end_line=min(len(lines), index + 12),
                )
            )
            self.chunking.add_chunk(
                repository,
                file_record.path,
                symbol_type,
                "\n".join(lines[index - 1 : index + 12]),
                index,
                min(len(lines), index + 12),
                name,
            )

    def _parse_imports_and_api_calls(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        for index, line in enumerate(text.splitlines(), start=1):
            import_match = self.import_pattern.search(line)
            if import_match:
                self._add_import_relation(repository, file_record.path, import_match.group(1), 0.75)

            api_match = self.api_pattern.search(line)
            if api_match:
                method = api_match.group(2).upper() if api_match.group(2) else "GET"
                route_path = api_match.group(3)
                self.chunking.add_chunk(repository, file_record.path, "api_call", line, index, index, f"{method} {route_path}")
                repository.graph_nodes.append(
                    GraphNodeDTO(
                        id=stable_node_id(repository.id, "api_call", f"{file_record.path}:{index}:{method}:{route_path}"),
                        type="api_call",
                        label=f"{method} {route_path}",
                        file_path=file_record.path,
                        start_line=index,
                        end_line=index,
                        scope_path=file_record.path,
                        role="API call",
                    )
                )

    def _add_import_relation(self, repository: RepositoryState, file_path: str, module: str, confidence: float) -> None:
        module_ref = module.strip()
        if not module_ref:
            return
        module_node = node_id("module", module_ref)
        repository.graph_nodes.append(GraphNodeDTO(id=module_node, type="module", label=module_ref, file_path=None))
        repository.graph_edges.append(GraphEdgeDTO(source=node_id("file", file_path), target=module_node, type="imports", confidence=confidence))
