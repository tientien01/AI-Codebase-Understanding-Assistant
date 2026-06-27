from __future__ import annotations

import ast
import re
from uuid import uuid4

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO
from app.services.chunking_service import ChunkingService
from app.services.index_models import EndpointRecord, FileRecord, RepositoryState, SymbolRecord
from app.services.text_utils import node_id, read_text


class ParserService:
    def __init__(self, chunking: ChunkingService | None = None) -> None:
        self.chunking = chunking or ChunkingService()
        self.function_pattern = re.compile(r"(?:function\s+([A-Z_a-z][\w]*)|const\s+([A-Z_a-z][\w]*)\s*=\s*(?:async\s*)?\(?[^=]*\)?\s*=>)")
        self.api_pattern = re.compile(r"(axios\.(get|post|put|delete|patch)|fetch)\s*\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
        self.import_pattern = re.compile(r"^\s*import\s+(?:.+?\s+from\s+)?['\"]([^'\"]+)['\"]")

    def parse_files(self, repository: RepositoryState) -> None:
        for file_record in repository.files:
            try:
                text = read_text(file_record.absolute_path)
            except UnicodeDecodeError:
                repository.failed_files += 1
                file_record.parse_status = "failed"
                repository.warnings.append(f"Encoding error: {file_record.path}")
                continue

            if file_record.language == "python":
                self._parse_python(repository, file_record, text)
            elif file_record.language in {"javascript", "typescript"}:
                self._parse_js_ts(repository, file_record, text)
            elif file_record.language == "markdown":
                self._parse_markdown(repository, file_record, text)
            else:
                self.chunking.add_chunk(repository, file_record.path, "config_section", text, 1, max(1, len(text.splitlines())))

    def _parse_python(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            repository.failed_files += 1
            repository.warnings.append(f"Python parse error: {file_record.path}:{exc.lineno}")
            self.chunking.add_chunk(repository, file_record.path, "file_summary", text, 1, max(1, len(text.splitlines())))
            return

        lines = text.splitlines()
        self._extract_python_imports(repository, file_record, tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            symbol_type = "class" if isinstance(node, ast.ClassDef) else "function"
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", node.lineno)
            repository.symbols.append(
                SymbolRecord(
                    id=f"symbol_{uuid4().hex[:10]}",
                    name=node.name,
                    symbol_type=symbol_type,
                    file_path=file_record.path,
                    start_line=start_line,
                    end_line=end_line,
                    signature=self._python_signature(node),
                )
            )

            chunk_type = "class" if symbol_type == "class" else "function"
            self.chunking.add_chunk(
                repository,
                file_record.path,
                chunk_type,
                "\n".join(lines[start_line - 1 : end_line]),
                start_line,
                end_line,
                node.name,
            )

            endpoint = self._extract_fastapi_endpoint(node, file_record.path)
            if endpoint:
                repository.endpoints.append(endpoint)
                self.chunking.add_chunk(
                    repository,
                    file_record.path,
                    "endpoint",
                    "\n".join(lines[start_line - 1 : end_line]),
                    start_line,
                    end_line,
                    node.name,
                )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_python_calls(repository, file_record, node)

    def _parse_js_ts(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        lines = text.splitlines()
        for index, line in enumerate(lines, start=1):
            import_match = self.import_pattern.search(line)
            if import_match:
                self._add_import_relation(repository, file_record.path, import_match.group(1), 0.75)

            function_match = self.function_pattern.search(line)
            if function_match:
                name = function_match.group(1) or function_match.group(2)
                symbol_type = "component" if name[:1].isupper() else "function"
                repository.symbols.append(
                    SymbolRecord(
                        id=f"symbol_{uuid4().hex[:10]}",
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

            api_match = self.api_pattern.search(line)
            if api_match:
                method = api_match.group(2).upper() if api_match.group(2) else "GET"
                route_path = api_match.group(3)
                self.chunking.add_chunk(repository, file_record.path, "api_call", line, index, index, f"{method} {route_path}")
                repository.graph_nodes.append(
                    GraphNodeDTO(id=f"api_call_{uuid4().hex[:8]}", type="api_call", label=f"{method} {route_path}", file_path=file_record.path)
                )

    def _extract_python_imports(self, repository: RepositoryState, file_record: FileRecord, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._add_import_relation(repository, file_record.path, alias.name, 0.95)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self._add_import_relation(repository, file_record.path, node.module, 0.95)

    def _extract_python_calls(self, repository: RepositoryState, file_record: FileRecord, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
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
        repository.graph_edges.append(
            GraphEdgeDTO(source=node_id("file", file_path), target=module_node, type="imports", confidence=confidence)
        )

    def _parse_markdown(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        lines = text.splitlines()
        headings = [(index, line.strip("# ").strip()) for index, line in enumerate(lines, start=1) if line.startswith("#")]
        if not headings:
            self.chunking.add_chunk(repository, file_record.path, "doc_section", text, 1, max(1, len(lines)))
            return
        for position, (start, heading) in enumerate(headings):
            end = headings[position + 1][0] - 1 if position + 1 < len(headings) else len(lines)
            self.chunking.add_chunk(repository, file_record.path, "doc_section", "\n".join(lines[start - 1 : end]), start, end, heading)

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

    def _python_signature(self, node: ast.AST) -> str:
        if isinstance(node, ast.ClassDef):
            return f"class {node.name}"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args]
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            return f"{prefix} {node.name}({', '.join(args)})"
        return ""
