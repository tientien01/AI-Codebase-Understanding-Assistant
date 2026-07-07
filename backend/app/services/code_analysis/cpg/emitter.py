from __future__ import annotations

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO
from app.services.chunking_service import ChunkingService
from app.services.code_analysis.models import CFGGraph, CPGResult, DFGGraph, IRClass, IRFunction, IRModule, IRNode
from app.services.code_analysis.stable_ids import stable_node_id, stable_symbol_id
from app.services.index_models import EndpointRecord, RepositoryState, SymbolRecord
from app.services.text_utils import node_id


class CPGEmitter:
    def __init__(self, chunking: ChunkingService) -> None:
        self.chunking = chunking

    def apply(self, repository: RepositoryState, result: CPGResult) -> None:
        self._emit_imports(repository, result.module)
        for item in result.module.classes:
            self._emit_class(repository, item)
        for function in result.module.functions:
            self._emit_function(repository, function, "function")
        for endpoint in result.module.endpoints:
            repository.endpoints.append(
                EndpointRecord(
                    method=endpoint.method,
                    path=endpoint.path,
                    handler=endpoint.handler,
                    file_path=endpoint.file_path,
                    start_line=endpoint.start_line,
                    end_line=endpoint.end_line,
                )
            )
            self.chunking.add_chunk(
                repository,
                endpoint.file_path,
                "endpoint",
                f"{endpoint.method} {endpoint.path} -> {endpoint.handler_qualified_name}",
                endpoint.start_line,
                endpoint.end_line,
                endpoint.handler,
            )
        self._emit_cfg(repository, result.cfg_graphs)
        self._emit_dfg(repository, result.dfg_graphs)

    def _emit_imports(self, repository: RepositoryState, module: IRModule) -> None:
        file_node = node_id("file", module.file_path)
        for import_item in module.imports:
            self._add_import_edge(repository, file_node, import_item.module, 0.95)
            if import_item.imported_name:
                self._add_import_edge(repository, file_node, f"{import_item.module}.{import_item.imported_name}", 0.86)

    def _add_import_edge(self, repository: RepositoryState, file_node: str, module_label: str, confidence: float) -> None:
        module_node = node_id("module", module_label)
        repository.graph_nodes.append(GraphNodeDTO(id=module_node, type="module", label=module_label, file_path=None))
        repository.graph_edges.append(GraphEdgeDTO(source=file_node, target=module_node, type="imports", confidence=confidence))

    def _emit_class(self, repository: RepositoryState, item: IRClass) -> None:
        symbol_type = self._class_symbol_type(item)
        self._add_symbol(repository, item, item.name, item.qualified_name, symbol_type, f"class {item.name}")
        for child in item.body:
            if isinstance(child, IRFunction):
                self._emit_function(repository, child, "method")
            elif isinstance(child, IRClass):
                self._emit_class(repository, child)

    def _emit_function(self, repository: RepositoryState, function: IRFunction, default_type: str) -> None:
        self._add_symbol(
            repository,
            function,
            function.name,
            function.qualified_name,
            default_type,
            function.metadata.get("signature", f"def {function.name}"),
        )
        self._emit_call_edges(repository, function)

    def _add_symbol(
        self,
        repository: RepositoryState,
        node: IRNode,
        name: str,
        qualified_name: str,
        symbol_type: str,
        signature: str,
    ) -> None:
        repository.symbols.append(
            SymbolRecord(
                id=stable_symbol_id(repository.id, node.file_path, qualified_name, symbol_type),
                name=name,
                symbol_type=symbol_type,
                file_path=node.file_path,
                start_line=node.start_line,
                end_line=node.end_line,
                signature=signature,
            )
        )
        self.chunking.add_chunk(repository, node.file_path, symbol_type, node.text, node.start_line, node.end_line, name)

    def _emit_call_edges(self, repository: RepositoryState, function: IRFunction) -> None:
        source = node_id("symbol", f"{function.file_path}:{function.name}")
        for call_name in self._call_names(function.body):
            target = node_id("symbol", f"{function.file_path}:{call_name.split('.')[-1]}")
            repository.graph_edges.append(GraphEdgeDTO(source=source, target=target, type="calls", confidence=0.62))
            call_site_id = stable_node_id(repository.id, "call_site", f"{function.file_path}:{function.qualified_name}:{call_name}")
            repository.graph_nodes.append(
                GraphNodeDTO(
                    id=call_site_id,
                    type="call_site",
                    label=call_name,
                    file_path=function.file_path,
                    scope_path=function.file_path,
                    role="Call site",
                )
            )
            repository.graph_edges.append(GraphEdgeDTO(source=source, target=call_site_id, type="contains_call", confidence=0.8))

    def _call_names(self, statements) -> list[str]:
        names: list[str] = []
        for statement in statements:
            for expression in [*statement.expressions, *statement.targets]:
                names.extend(self._call_names_from_expression(expression))
            names.extend(self._call_names(statement.body))
            names.extend(self._call_names(statement.orelse))
            names.extend(self._call_names(statement.handlers))
        return names

    def _call_names_from_expression(self, expression) -> list[str]:
        names = [expression.name] if expression.kind == "call" and expression.name else []
        for child in expression.children:
            names.extend(self._call_names_from_expression(child))
        return names

    def _emit_cfg(self, repository: RepositoryState, graphs: list[CFGGraph]) -> None:
        for graph in graphs:
            for node in graph.nodes:
                repository.graph_nodes.append(
                    GraphNodeDTO(
                        id=node.id,
                        type="cfg_node",
                        label=node.label,
                        file_path=node.file_path,
                        scope_path=node.file_path,
                        role=node.kind,
                    )
                )
            for edge in graph.edges:
                repository.graph_edges.append(GraphEdgeDTO(source=edge.source, target=edge.target, type=edge.type, confidence=edge.confidence, evidence_level="inferred"))

    def _emit_dfg(self, repository: RepositoryState, graphs: list[DFGGraph]) -> None:
        for graph in graphs:
            for node in graph.nodes:
                repository.graph_nodes.append(
                    GraphNodeDTO(
                        id=node.id,
                        type="dfg_node",
                        label=f"{node.kind}: {node.name}",
                        file_path=node.file_path,
                        scope_path=node.file_path,
                        role=node.kind,
                    )
                )
            for edge in graph.edges:
                repository.graph_edges.append(GraphEdgeDTO(source=edge.source, target=edge.target, type=edge.type, confidence=edge.confidence, evidence_level="inferred"))

    def _class_symbol_type(self, item: IRClass) -> str:
        if "BaseModel" in item.bases:
            return "schema"
        if "Base" in item.bases:
            return "model"
        return "class"
