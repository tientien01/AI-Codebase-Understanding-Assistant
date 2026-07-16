from __future__ import annotations

import re
from pathlib import Path

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO, GraphResponse
from app.schemas.graph import GraphProjectionRequest
from app.services.graph.graph_projection_service import GraphProjectionService
from app.services.graph.graph_schema_service import GraphSchemaService
from app.services.index_models import EndpointRecord, RepositoryState
from app.services.text_utils import node_id, normalize_route


class GraphService:
    def __init__(self, schema: GraphSchemaService | None = None) -> None:
        self.schema = schema or GraphSchemaService()

    def get_graph(self, repository: RepositoryState, request: GraphProjectionRequest | None = None) -> GraphResponse:
        return GraphProjectionService().all(repository, request)

    def build_graph(self, repository: RepositoryState) -> None:
        nodes: dict[str, GraphNodeDTO] = {node.id: node for node in repository.graph_nodes}
        edges: list[GraphEdgeDTO] = list(repository.graph_edges)
        root_id = node_id("folder", ".")
        nodes[root_id] = GraphNodeDTO(id=root_id, type="folder", label=repository.name, coverage="mapped", scope_path="", role="Project")

        for file_record in repository.files:
            self._add_folder_path(nodes, edges, root_id, file_record.path)
            file_id = node_id("file", file_record.path)
            parent_id = self._folder_id_for_file(file_record.path)
            nodes[file_id] = GraphNodeDTO(
                id=file_id,
                type="file",
                label=Path(file_record.path).name,
                file_path=file_record.path,
                coverage="deep_indexed",
                scope_path=file_record.path,
                role=self._file_role(file_record.path, file_record.language),
            )
            edges.append(GraphEdgeDTO(source=parent_id, target=file_id, type="contains", confidence=0.95, evidence_level="map"))

        for symbol in repository.symbols:
            file_id = node_id("file", symbol.file_path)
            nodes[symbol.id] = GraphNodeDTO(
                id=symbol.id,
                type=symbol.symbol_type,
                label=symbol.name,
                file_path=symbol.file_path,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                coverage="deep_indexed",
                scope_path=symbol.file_path,
                role=symbol.symbol_type,
            )
            edges.append(GraphEdgeDTO(source=file_id, target=symbol.id, type="defines", confidence=0.95))

        handler_symbols = {
            (symbol.file_path, symbol.name): symbol.id
            for symbol in repository.symbols
            if symbol.symbol_type in {"function", "method"}
        }
        for endpoint in repository.endpoints:
            endpoint_id = node_id("endpoint", f"{endpoint.method}:{endpoint.path}")
            handler_id = handler_symbols.get((endpoint.file_path, endpoint.handler))
            nodes[endpoint_id] = GraphNodeDTO(
                id=endpoint_id,
                type="endpoint",
                label=f"{endpoint.method} {endpoint.path}",
                file_path=endpoint.file_path,
                start_line=endpoint.start_line,
                end_line=endpoint.end_line,
                coverage="deep_indexed",
                scope_path=endpoint.file_path,
                role="API endpoint",
            )
            if handler_id:
                edges.append(GraphEdgeDTO(source=endpoint_id, target=handler_id, type="exposes_endpoint", confidence=0.9))

        endpoints_by_signature: dict[tuple[str, str], list[EndpointRecord]] = {}
        for endpoint in repository.endpoints:
            signature = (endpoint.method.upper(), self._route_shape(endpoint.path))
            endpoints_by_signature.setdefault(signature, []).append(endpoint)
        for graph_node in list(repository.graph_nodes):
            if graph_node.type != "api_call":
                continue
            method, route = self._api_call_signature(graph_node.label)
            if method is None or route is None:
                continue
            route_shape = self._route_shape(route)
            candidates = endpoints_by_signature.get((method, route_shape), [])
            if not candidates:
                candidates = [
                    candidate
                    for candidate in repository.endpoints
                    if candidate.method.upper() == method
                    and self._route_suffix_matches(route_shape, self._route_shape(candidate.path))
                ]
            if len(candidates) != 1:
                continue
            endpoint = candidates[0]
            endpoint_id = node_id("endpoint", f"{endpoint.method}:{endpoint.path}")
            edges.append(GraphEdgeDTO(source=graph_node.id, target=endpoint_id, type="calls_api", confidence=0.72))

        repository.graph_nodes = list(nodes.values())
        repository.graph_edges = self._dedupe_edges(edges)
        self.schema.normalize_repository_graph(repository)

    def _api_call_signature(self, label: str) -> tuple[str | None, str | None]:
        parts = label.strip().split(" ", 1)
        if len(parts) != 2:
            return None, None
        method, route = parts[0].upper(), parts[1].strip()
        if method not in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"} or not route:
            return None, None
        return method, route

    def _route_shape(self, route: str) -> str:
        normalized = normalize_route(route.split("?", 1)[0])
        normalized = re.sub(r"\{[^/{}]+\}", "{}", normalized)
        normalized = re.sub(r":[A-Za-z_$][\w$]*", "{}", normalized)
        return normalized

    def _route_suffix_matches(self, client_route: str, endpoint_route: str) -> bool:
        return endpoint_route != "/" and client_route.endswith(endpoint_route)

    def _add_folder_path(self, nodes: dict[str, GraphNodeDTO], edges: list[GraphEdgeDTO], root_id: str, file_path: str) -> None:
        parts = Path(file_path).parts[:-1]
        parent_id = root_id
        current_parts: list[str] = []
        for part in parts:
            current_parts.append(part)
            folder_path = "/".join(current_parts)
            folder_id = node_id("folder", folder_path)
            nodes.setdefault(
                folder_id,
                GraphNodeDTO(
                    id=folder_id,
                    type="folder",
                    label=part,
                    coverage="mapped",
                    scope_path=folder_path,
                    role=self._folder_role(folder_path),
                ),
            )
            edges.append(GraphEdgeDTO(source=parent_id, target=folder_id, type="contains", confidence=0.85, evidence_level="map"))
            parent_id = folder_id

    def _folder_id_for_file(self, file_path: str) -> str:
        parent = Path(file_path).parent.as_posix()
        return node_id("folder", "." if parent == "." else parent)

    def _folder_role(self, folder_path: str) -> str:
        lower = folder_path.lower()
        if "frontend" in lower or lower.startswith("apps/web"):
            return "Frontend area"
        if "backend" in lower or "service" in lower:
            return "Backend service"
        if "test" in lower:
            return "Tests"
        if "doc" in lower:
            return "Documentation"
        return "Project area"

    def _file_role(self, file_path: str, language: str) -> str:
        name = Path(file_path).name.lower()
        if name.startswith("readme"):
            return "Documentation"
        if name in {"main.py", "app.py", "server.py"}:
            return "Entrypoint"
        if "route" in file_path.lower() or "controller" in file_path.lower():
            return "API routing"
        return f"{language.title()} file"

    def _dedupe_edges(self, edges: list[GraphEdgeDTO]) -> list[GraphEdgeDTO]:
        deduped: dict[tuple[str, str, str], GraphEdgeDTO] = {}
        for edge in edges:
            key = (edge.source, edge.target, edge.type)
            existing = deduped.get(key)
            if existing is None or edge.confidence > existing.confidence:
                deduped[key] = edge
        return list(deduped.values())
