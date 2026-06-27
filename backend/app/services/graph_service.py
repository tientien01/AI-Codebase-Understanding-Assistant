from __future__ import annotations

from pathlib import Path

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO
from app.services.index_models import RepositoryState
from app.services.text_utils import node_id, normalize_route


class GraphService:
    def build_graph(self, repository: RepositoryState) -> None:
        nodes: dict[str, GraphNodeDTO] = {node.id: node for node in repository.graph_nodes}
        edges: list[GraphEdgeDTO] = list(repository.graph_edges)

        for file_record in repository.files:
            file_id = node_id("file", file_record.path)
            nodes[file_id] = GraphNodeDTO(id=file_id, type="file", label=Path(file_record.path).name, file_path=file_record.path)

        for symbol in repository.symbols:
            symbol_id = node_id("symbol", f"{symbol.file_path}:{symbol.name}")
            file_id = node_id("file", symbol.file_path)
            nodes[symbol_id] = GraphNodeDTO(id=symbol_id, type=symbol.symbol_type, label=symbol.name, file_path=symbol.file_path)
            edges.append(GraphEdgeDTO(source=file_id, target=symbol_id, type="defines", confidence=0.95))

        for endpoint in repository.endpoints:
            endpoint_id = node_id("endpoint", f"{endpoint.method}:{endpoint.path}")
            handler_id = node_id("symbol", f"{endpoint.file_path}:{endpoint.handler}")
            nodes[endpoint_id] = GraphNodeDTO(id=endpoint_id, type="endpoint", label=f"{endpoint.method} {endpoint.path}", file_path=endpoint.file_path)
            edges.append(GraphEdgeDTO(source=endpoint_id, target=handler_id, type="exposes_endpoint", confidence=0.9))

        endpoint_by_path = {normalize_route(endpoint.path): endpoint for endpoint in repository.endpoints}
        for graph_node in list(repository.graph_nodes):
            if graph_node.type != "api_call":
                continue
            route = graph_node.label.split(" ", 1)[-1]
            normalized_route = normalize_route(route)
            endpoint = endpoint_by_path.get(normalized_route)
            if endpoint is None:
                endpoint = next(
                    (
                        candidate
                        for candidate in repository.endpoints
                        if normalized_route.endswith(normalize_route(candidate.path))
                    ),
                    None,
                )
            if not endpoint:
                continue
            endpoint_id = node_id("endpoint", f"{endpoint.method}:{endpoint.path}")
            edges.append(GraphEdgeDTO(source=graph_node.id, target=endpoint_id, type="calls_api", confidence=0.72))

        repository.graph_nodes = list(nodes.values())
        repository.graph_edges = edges
