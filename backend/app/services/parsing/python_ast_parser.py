from __future__ import annotations

import ast

from app.services.chunking_service import ChunkingService
from app.services.code_analysis.stable_ids import stable_symbol_id
from app.services.index_models import EndpointRecord, FileRecord, RepositoryState, SymbolRecord
from app.services.parsing.base import LanguageParser
from app.services.text_utils import node_id
from app.schemas.api import GraphEdgeDTO, GraphNodeDTO
from app.services.code_analysis.pipeline import CodeAnalysisPipeline


class PythonAstParser(LanguageParser):
    def __init__(self, chunking: ChunkingService) -> None:
        self.chunking = chunking
        self.code_analysis = CodeAnalysisPipeline(chunking)

    def parse(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        try:
            if self.code_analysis.parse_python(repository, file_record, text):
                return
        except Exception as exc:
            repository.warnings.append(f"Python code analysis fallback: {file_record.path}: {exc}")

        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            repository.failed_files += 1
            file_record.parse_status = "failed"
            repository.warnings.append(f"Python parse error: {file_record.path}:{exc.lineno}")
            repository.failed_file_records.append(
                {
                    "file_path": file_record.path,
                    "stage": "parsing_files",
                    "error_code": "PARSER_ERROR",
                    "message": "Python syntax error. File was skipped by the AST parser.",
                    "line": exc.lineno,
                }
            )
            self.chunking.add_chunk(repository, file_record.path, "file_summary", text, 1, max(1, len(text.splitlines())))
            return

        lines = text.splitlines()
        self._extract_imports(repository, file_record, tree)
        self._parse_body(repository, file_record, lines, tree.body)

    def _parse_body(
        self,
        repository: RepositoryState,
        file_record: FileRecord,
        lines: list[str],
        body: list[ast.stmt],
        parent_class: str | None = None,
    ) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                symbol_type = self._class_type(node)
                self._add_symbol(repository, file_record, lines, node, symbol_type)
                self._parse_body(repository, file_record, lines, node.body, node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbol_type = "method" if parent_class else "function"
                self._add_symbol(repository, file_record, lines, node, symbol_type)
                endpoint = self._extract_fastapi_endpoint(node, file_record.path)
                if endpoint:
                    repository.endpoints.append(endpoint)
                    start_line = getattr(node, "lineno", 1)
                    end_line = getattr(node, "end_lineno", start_line)
                    self.chunking.add_chunk(
                        repository,
                        file_record.path,
                        "endpoint",
                        "\n".join(lines[start_line - 1 : end_line]),
                        start_line,
                        end_line,
                        node.name,
                    )
                self._extract_calls(repository, file_record, node)

    def _add_symbol(
        self,
        repository: RepositoryState,
        file_record: FileRecord,
        lines: list[str],
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        symbol_type: str,
    ) -> None:
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", node.lineno)
        repository.symbols.append(
            SymbolRecord(
                id=stable_symbol_id(repository.id, file_record.path, node.name, symbol_type),
                name=node.name,
                symbol_type=symbol_type,
                file_path=file_record.path,
                start_line=start_line,
                end_line=end_line,
                signature=self._signature(node),
            )
        )
        self.chunking.add_chunk(
            repository,
            file_record.path,
            symbol_type,
            "\n".join(lines[start_line - 1 : end_line]),
            start_line,
            end_line,
            node.name,
        )

    def _class_type(self, node: ast.ClassDef) -> str:
        base_names = {self._call_name(base) or getattr(base, "id", "") for base in node.bases}
        if "BaseModel" in base_names:
            return "schema"
        if "Base" in base_names:
            return "model"
        return "class"

    def _extract_imports(self, repository: RepositoryState, file_record: FileRecord, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._add_import_relation(repository, file_record.path, alias.name, 0.95)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self._add_import_relation(repository, file_record.path, node.module, 0.95)

    def _extract_calls(self, repository: RepositoryState, file_record: FileRecord, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        source = node_id("symbol", f"{file_record.path}:{node.name}")
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            call_name = self._call_name(child.func)
            if not call_name:
                continue
            target = node_id("symbol", f"{file_record.path}:{call_name}")
            repository.graph_edges.append(GraphEdgeDTO(source=source, target=target, type="calls", confidence=0.62))

    def _call_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _add_import_relation(self, repository: RepositoryState, file_path: str, module: str, confidence: float) -> None:
        module_ref = module.strip()
        if not module_ref:
            return
        module_node = node_id("module", module_ref)
        repository.graph_nodes.append(GraphNodeDTO(id=module_node, type="module", label=module_ref, file_path=None))
        repository.graph_edges.append(GraphEdgeDTO(source=node_id("file", file_path), target=module_node, type="imports", confidence=confidence))

    def _extract_fastapi_endpoint(self, node: ast.AST, file_path: str) -> EndpointRecord | None:
        decorators = getattr(node, "decorator_list", [])
        for decorator in decorators:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            return EndpointRecord(
                method=decorator.func.attr.upper(),
                path=str(decorator.args[0].value),
                handler=getattr(node, "name", "handler"),
                file_path=file_path,
                start_line=getattr(node, "lineno", 1),
                end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            )
        return None

    def _signature(self, node: ast.AST) -> str:
        if isinstance(node, ast.ClassDef):
            return f"class {node.name}"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args]
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            return f"{prefix} {node.name}({', '.join(args)})"
        return ""
