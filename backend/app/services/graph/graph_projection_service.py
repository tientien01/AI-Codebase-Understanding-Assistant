from __future__ import annotations

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO, GraphResponse
from app.services.index_models import RepositoryState


class GraphProjectionService:
    def __init__(self, max_nodes: int = 220, max_edges: int = 520) -> None:
        self.max_nodes = max_nodes
        self.max_edges = max_edges

    def project_map(self, repository: RepositoryState) -> GraphResponse:
        return self._subgraph(
            repository,
            node_types={"folder", "file", "endpoint", "component", "class", "function", "method", "schema", "model"},
            edge_types={"contains", "defines", "exposes_endpoint"},
        )

    def dependencies(self, repository: RepositoryState, file_path: str | None = None) -> GraphResponse:
        edges = [edge for edge in repository.graph_edges if edge.type == "imports"]
        if file_path:
            file_node_ids = {node.id for node in repository.graph_nodes if node.file_path == file_path or node.scope_path == file_path}
            edges = [edge for edge in edges if edge.source in file_node_ids or edge.target in file_node_ids]
        return self._from_edges(repository, edges)

    def api_flow(self, repository: RepositoryState, endpoint_id: str | None = None) -> GraphResponse:
        edges = [edge for edge in repository.graph_edges if edge.type in {"calls_api", "exposes_endpoint", "contains_call", "calls"}]
        if endpoint_id:
            edges = [edge for edge in edges if edge.source == endpoint_id or edge.target == endpoint_id]
        node_ids = self._node_ids_from_edges(edges)
        api_nodes = {
            node.id
            for node in repository.graph_nodes
            if node.type in {"endpoint", "api_call", "call_site"} or node.id in node_ids
        }
        return self._subgraph_by_ids(repository, api_nodes, edges)

    def function_flow(self, repository: RepositoryState, symbol_id: str | None = None) -> GraphResponse:
        edges = [edge for edge in repository.graph_edges if edge.type.startswith("cfg_") or edge.type in {"calls", "contains_call"}]
        if symbol_id:
            related = self._reachable_node_ids(edges, symbol_id, depth=2)
            edges = [edge for edge in edges if edge.source in related or edge.target in related]
        node_ids = self._node_ids_from_edges(edges)
        flow_nodes = {
            node.id
            for node in repository.graph_nodes
            if node.type in {"cfg_node", "call_site", "function", "method"} and (not node_ids or node.id in node_ids)
        }
        return self._subgraph_by_ids(repository, flow_nodes | node_ids, edges)

    def data_flow(self, repository: RepositoryState, symbol_id: str | None = None) -> GraphResponse:
        edges = [edge for edge in repository.graph_edges if edge.type.startswith("dfg_")]
        if symbol_id:
            related = self._reachable_node_ids(edges, symbol_id, depth=3)
            edges = [edge for edge in edges if edge.source in related or edge.target in related]
        return self._from_edges(repository, edges)

    def _subgraph(
        self,
        repository: RepositoryState,
        node_types: set[str],
        edge_types: set[str],
    ) -> GraphResponse:
        nodes = [node for node in repository.graph_nodes if node.type in node_types]
        node_ids = {node.id for node in nodes}
        edges = [
            edge
            for edge in repository.graph_edges
            if edge.type in edge_types and edge.source in node_ids and edge.target in node_ids
        ]
        return self._limit(nodes, edges)

    def _from_edges(self, repository: RepositoryState, edges: list[GraphEdgeDTO]) -> GraphResponse:
        return self._subgraph_by_ids(repository, self._node_ids_from_edges(edges), edges)

    def _subgraph_by_ids(self, repository: RepositoryState, node_ids: set[str], edges: list[GraphEdgeDTO]) -> GraphResponse:
        nodes = [node for node in repository.graph_nodes if node.id in node_ids]
        visible = {node.id for node in nodes}
        filtered_edges = [edge for edge in edges if edge.source in visible and edge.target in visible]
        return self._limit(nodes, filtered_edges)

    def _limit(self, nodes: list[GraphNodeDTO], edges: list[GraphEdgeDTO]) -> GraphResponse:
        limited_nodes = nodes[: self.max_nodes]
        visible = {node.id for node in limited_nodes}
        limited_edges = [edge for edge in edges if edge.source in visible and edge.target in visible][: self.max_edges]
        return GraphResponse(nodes=limited_nodes, edges=limited_edges)

    def _node_ids_from_edges(self, edges: list[GraphEdgeDTO]) -> set[str]:
        ids: set[str] = set()
        for edge in edges:
            ids.add(edge.source)
            ids.add(edge.target)
        return ids

    def _reachable_node_ids(self, edges: list[GraphEdgeDTO], root_id: str, depth: int) -> set[str]:
        related = {root_id}
        frontier = {root_id}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for edge in edges:
                if edge.source in frontier:
                    next_frontier.add(edge.target)
                if edge.target in frontier:
                    next_frontier.add(edge.source)
            related.update(next_frontier)
            frontier = next_frontier
            if not frontier:
                break
        return related
