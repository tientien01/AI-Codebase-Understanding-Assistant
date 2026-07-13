from __future__ import annotations

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO
from app.services.chunking_service import ChunkingService
from app.services.code_analysis.models import (
    CFGGraph,
    CPGResult,
    DFGGraph,
    IRClass,
    IRFunction,
    IRModule,
    IRNode,
    ResolvedReference,
    canonical_symbol_key,
)
from app.services.code_analysis.stable_ids import stable_node_id, stable_symbol_id
from app.services.index_models import EndpointRecord, RepositoryState, SymbolRecord
from app.services.text_utils import node_id


class CPGEmitter:
    def __init__(self, chunking: ChunkingService) -> None:
        self.chunking = chunking

    def apply(self, repository: RepositoryState, result: CPGResult) -> None:
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
                    metadata=endpoint.metadata,
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
        if result.references is not None:
            repository.resolved_references.extend(result.references.references)
            self._emit_references(repository, result.module, result.references.references)
        self._emit_cfg(repository, result.cfg_graphs)
        self._emit_dfg(repository, result.dfg_graphs)

    def _add_import_edge(self, repository: RepositoryState, file_node: str, module_label: str, confidence: float) -> None:
        module_node = node_id("module", module_label)
        repository.graph_nodes.append(GraphNodeDTO(id=module_node, type="module", label=module_label, file_path=None))
        repository.graph_edges.append(GraphEdgeDTO(source=file_node, target=module_node, type="imports", confidence=confidence))


    def _emit_class(
        self,
        repository: RepositoryState,
        item: IRClass,
    ) -> None:
        symbol_type = self._class_symbol_type(item)
        self._add_symbol(repository, item, item.name, item.qualified_name, symbol_type, f"class {item.name}")
        for child in item.body:
            if isinstance(child, IRFunction):
                self._emit_function(repository, child, "method")
            elif isinstance(child, IRClass):
                self._emit_class(repository, child)

    def _emit_function(
        self,
        repository: RepositoryState,
        function: IRFunction,
        default_type: str,
    ) -> None:
        self._add_symbol(
            repository,
            function,
            function.name,
            function.qualified_name,
            default_type,
            function.metadata.get("signature", f"def {function.name}"),
        )

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

    def _emit_references(
        self,
        repository: RepositoryState,
        module: IRModule,
        references: tuple[ResolvedReference, ...],
    ) -> None:
        symbol_targets = self._canonical_symbol_targets(repository.id, module)
        for reference in references:
            if reference.reference_type == "import":
                self._emit_import_reference(repository, module, reference)
            else:
                self._emit_call_reference(repository, module, reference, symbol_targets)

    def _emit_import_reference(self, repository: RepositoryState, module: IRModule, reference: ResolvedReference) -> None:
        source = node_id("file", module.file_path)
        module_label = reference.raw_reference.rsplit(".", 1)[0] if "." in reference.raw_reference else reference.raw_reference
        self._add_import_edge(repository, source, module_label, 0.95)
        if reference.outcome == "resolved":
            target_path = self._file_path_from_key(reference.target_keys[0])
            repository.graph_edges.append(
                GraphEdgeDTO(source=source, target=node_id("file", target_path), type="imports_internal", confidence=0.88)
            )

    def _emit_call_reference(
        self,
        repository: RepositoryState,
        module: IRModule,
        reference: ResolvedReference,
        symbol_targets: dict[str, str],
    ) -> None:
        source = symbol_targets.get(reference.source_entity_key or "", node_id("file", module.file_path))
        if reference.outcome == "resolved":
            target = symbol_targets[reference.target_keys[0]]
            edge_type, confidence = "calls", 0.76
        else:
            node_type, edge_type, confidence = self._unresolved_projection(reference)
            target = self._external_call_node(repository, module.file_path, reference.raw_reference, node_type)
            if reference.unresolved_reason == "target_not_found" or reference.outcome == "ambiguous":
                repository.parse_diagnostics.append(
                    {
                        "file_path": module.file_path,
                        "language": "python",
                        "parser": "python-static-resolver/1",
                        "stage": "call_resolution",
                        "severity": "warning",
                        "message": (
                            f"Ambiguous call target '{reference.raw_reference}'."
                            if reference.outcome == "ambiguous"
                            else f"Could not resolve call target '{reference.raw_reference}'."
                        ),
                        "line": reference.source_spans[0].start_line,
                    }
                )
        repository.graph_edges.append(GraphEdgeDTO(source=source, target=target, type=edge_type, confidence=confidence))
        call_site_id = stable_node_id(repository.id, "call_site", reference.canonical_key)
        repository.graph_nodes.append(
            GraphNodeDTO(
                id=call_site_id,
                type="call_site",
                label=reference.raw_reference,
                file_path=module.file_path,
                start_line=reference.source_spans[0].start_line,
                end_line=reference.source_spans[0].end_line,
                scope_path=module.file_path,
                role="Call site",
            )
        )
        repository.graph_edges.append(GraphEdgeDTO(source=source, target=call_site_id, type="contains_call", confidence=0.8))

    def _unresolved_projection(self, reference: ResolvedReference) -> tuple[str, str, float]:
        mapping = {
            "builtin_target": ("builtin_call", "calls_builtin", 0.92),
            "stdlib_target": ("stdlib_call", "calls_stdlib", 0.84),
            "framework_target": ("framework_call", "calls_framework", 0.86),
            "external_target": ("external_call", "calls_external", 0.68),
        }
        return mapping.get(reference.unresolved_reason or "", ("unresolved_call", "calls_unresolved", 0.25))

    def _external_call_node(self, repository: RepositoryState, file_path: str, call_name: str, node_type: str) -> str:
        node_id_value = stable_node_id(repository.id, node_type, f"{file_path}:{call_name}")
        repository.graph_nodes.append(
            GraphNodeDTO(
                id=node_id_value,
                type=node_type,
                label=call_name,
                file_path=file_path,
                scope_path=file_path,
                role=node_type,
            )
        )
        return node_id_value

    def _canonical_symbol_targets(self, repository_id: str, module: IRModule) -> dict[str, str]:
        index: dict[str, str] = {}
        for function in module.functions:
            symbol_id = stable_symbol_id(repository_id, function.file_path, function.qualified_name, "function")
            index[canonical_symbol_key(module.file_key, function.qualified_name, "function")] = symbol_id
        for item in module.classes:
            self._index_class_symbols(repository_id, module.file_key, index, item)
        return index

    def _index_class_symbols(self, repository_id: str, file_key: str, index: dict[str, str], item: IRClass) -> None:
        for child in item.body:
            if isinstance(child, IRFunction):
                symbol_id = stable_symbol_id(repository_id, child.file_path, child.qualified_name, "method")
                index[canonical_symbol_key(file_key, child.qualified_name, "method")] = symbol_id
            elif isinstance(child, IRClass):
                self._index_class_symbols(repository_id, file_key, index, child)

    def _file_path_from_key(self, file_key: str) -> str:
        from urllib.parse import unquote

        return unquote(file_key.removeprefix("file:v1:"))

    def _emit_cfg(self, repository: RepositoryState, graphs: list[CFGGraph]) -> None:
        for graph in graphs:
            for node in graph.nodes:
                repository.graph_nodes.append(
                    GraphNodeDTO(
                        id=node.id,
                        type="cfg_node",
                        label=node.label,
                        file_path=node.file_path,
                        start_line=node.start_line,
                        end_line=node.end_line,
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
                        start_line=node.line,
                        end_line=node.line,
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
