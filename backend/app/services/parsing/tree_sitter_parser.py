from __future__ import annotations

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO
from app.services.code_analysis.stable_ids import stable_chunk_id, stable_node_id, stable_symbol_id, unique_definition_id
from app.services.index_models import FileRecord, RepositoryState, SymbolRecord
from app.services.language_registry import LanguageDefinition
from app.services.parsing.base import LanguageParser
from app.services.text_utils import node_id

try:
    from tree_sitter_language_pack import get_parser
except ImportError:  # pragma: no cover - exercised when optional dependency is absent.
    get_parser = None


SYMBOL_NODE_TYPES = {
    "class_declaration": "class",
    "class_definition": "class",
    "enum_declaration": "enum",
    "enum_item": "enum",
    "function_declaration": "function",
    "function_definition": "function",
    "function_item": "function",
    "interface_declaration": "interface",
    "method_declaration": "method",
    "method_definition": "method",
    "struct_declaration": "struct",
    "struct_item": "struct",
    "trait_item": "interface",
}
IMPORT_NODE_TYPES = {
    "import_declaration",
    "import_statement",
    "package_import_declaration",
    "require_call",
    "scoped_use_list",
    "use_declaration",
    "use_item",
    "using_directive",
}
CALL_NODE_TYPES = {
    "call_expression",
    "invocation_expression",
    "method_invocation",
}


class TreeSitterLanguageParser(LanguageParser):
    def __init__(self, definition: LanguageDefinition) -> None:
        self.definition = definition
        self._parser = None

    @property
    def available(self) -> bool:
        return get_parser is not None and self.definition.tree_sitter_language is not None

    def parse(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        if not self.available:
            return
        parser = self._get_parser()
        if parser is None:
            return
        content = text.encode("utf-8")
        tree = parser.parse(content)
        self._walk(repository, file_record, text.splitlines(), content, tree.root_node)

    def _get_parser(self):
        if self._parser is not None:
            return self._parser
        if get_parser is None or self.definition.tree_sitter_language is None:
            return None
        try:
            self._parser = get_parser(self.definition.tree_sitter_language)
        except Exception:
            self._parser = None
        return self._parser

    def _walk(self, repository: RepositoryState, file_record: FileRecord, lines: list[str], content: bytes, node) -> None:
        if node.type in SYMBOL_NODE_TYPES:
            self._add_symbol(repository, file_record, lines, content, node)
        elif node.type in IMPORT_NODE_TYPES:
            self._add_import_relation(repository, file_record.path, content, node)
        elif node.type in CALL_NODE_TYPES:
            self._add_call_relation(repository, file_record.path, content, node)

        for child in node.children:
            self._walk(repository, file_record, lines, content, child)

    def _add_symbol(self, repository: RepositoryState, file_record: FileRecord, lines: list[str], content: bytes, node) -> None:
        name_node = self._name_node(node)
        name = self._node_text(content, name_node or node).strip()
        if not name:
            return
        start_line = self._row(node.start_point) + 1
        end_line = self._row(node.end_point) + 1
        symbol_type = SYMBOL_NODE_TYPES[node.type]
        repository.symbols.append(
            SymbolRecord(
                id=unique_definition_id(
                    stable_symbol_id(repository.id, file_record.path, name, symbol_type),
                    (item.id for item in repository.symbols),
                ),
                name=name,
                symbol_type=symbol_type,
                file_path=file_record.path,
                start_line=start_line,
                end_line=end_line,
                signature=self._first_line(lines, start_line),
            )
        )
        repository.chunks.append(
            self._chunk_from_lines(repository, file_record.path, symbol_type, lines, start_line, end_line, name)
        )

    def _add_import_relation(self, repository: RepositoryState, file_path: str, content: bytes, node) -> None:
        label = self._node_text(content, node).strip().replace("\n", " ")
        if not label:
            return
        module_id = node_id("module", label)
        repository.graph_nodes.append(GraphNodeDTO(id=module_id, type="module", label=label[:120], file_path=None))
        repository.graph_edges.append(GraphEdgeDTO(source=node_id("file", file_path), target=module_id, type="imports", confidence=0.72))

    def _add_call_relation(self, repository: RepositoryState, file_path: str, content: bytes, node) -> None:
        call_target = self._node_text(content, node.child_by_field_name("function") or node).split("(", 1)[0].strip()
        if not call_target:
            return
        target = stable_node_id(repository.id, "unresolved_call", f"{file_path}:{call_target}")
        repository.graph_nodes.append(
            GraphNodeDTO(
                id=target,
                type="unresolved_call",
                label=call_target,
                file_path=file_path,
                start_line=self._row(node.start_point) + 1,
                end_line=self._row(node.end_point) + 1,
                scope_path=file_path,
                role="Unresolved call",
            )
        )
        repository.graph_edges.append(
            GraphEdgeDTO(
                source=node_id("file", file_path),
                target=target,
                type="calls",
                confidence=0.45,
                evidence_level="inferred",
            )
        )

    def _name_node(self, node):
        for field_name in ("name", "declarator"):
            child = node.child_by_field_name(field_name)
            if child is not None:
                nested_name = child.child_by_field_name("name")
                return nested_name or child
        return None

    def _chunk_from_lines(
        self,
        repository: RepositoryState,
        file_path: str,
        chunk_type: str,
        lines: list[str],
        start_line: int,
        end_line: int,
        symbol_name: str,
    ):
        from app.services.index_models import ChunkRecord
        from app.services.text_utils import content_hash

        content = "\n".join(lines[start_line - 1 : end_line]).strip()
        digest = content_hash(f"{file_path}:{start_line}:{end_line}:{content}")
        return ChunkRecord(
            id=stable_chunk_id(repository.id, file_path, chunk_type, symbol_name, digest),
            file_path=file_path,
            chunk_type=chunk_type,
            content=content,
            start_line=start_line,
            end_line=max(start_line, end_line),
            symbol_name=symbol_name,
            content_hash=digest,
        )

    def _first_line(self, lines: list[str], start_line: int) -> str:
        if start_line < 1 or start_line > len(lines):
            return ""
        return lines[start_line - 1].strip()

    def _node_text(self, content: bytes, node) -> str:
        return content[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def _row(self, point) -> int:
        return point[0] if isinstance(point, tuple) else point.row
