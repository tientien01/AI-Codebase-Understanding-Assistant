from __future__ import annotations

from app.schemas.graph import (
    GraphEdgeDTO,
    GraphNodeDTO,
    GraphProjectionCounts,
    GraphProjectionCoverage,
    GraphProjectionProvenance,
    GraphProjectionRequest,
    GraphProjectionTruncation,
    GraphResponse,
)
from app.services.index_models import RepositoryState


class GraphProjectionVersionMismatch(ValueError):
    """Raised when a client asks for a non-active compatibility index version."""


class GraphProjectionService:
    def __init__(self, max_nodes: int = 220, max_edges: int = 520) -> None:
        self.max_nodes = max_nodes
        self.max_edges = max_edges

    def all(self, repository: RepositoryState, request: GraphProjectionRequest | None = None) -> GraphResponse:
        return self._project(repository, "all", request, repository.graph_nodes, repository.graph_edges)

    def project_map(self, repository: RepositoryState, request: GraphProjectionRequest | None = None) -> GraphResponse:
        return self._subgraph(
            repository,
            "project-map",
            request,
            node_types={"folder", "file", "endpoint", "component", "class", "function", "method", "schema", "model"},
            edge_types={"contains", "defines", "exposes_endpoint"},
        )

    def dependencies(
        self,
        repository: RepositoryState,
        file_path: str | None = None,
        request: GraphProjectionRequest | None = None,
    ) -> GraphResponse:
        edges = [edge for edge in repository.graph_edges if edge.type == "imports"]
        if file_path:
            file_node_ids = {node.id for node in repository.graph_nodes if node.file_path == file_path or node.scope_path == file_path}
            edges = [edge for edge in edges if edge.source in file_node_ids or edge.target in file_node_ids]
        return self._from_edges(repository, "dependencies", request, edges)

    def api_flow(
        self,
        repository: RepositoryState,
        endpoint_id: str | None = None,
        request: GraphProjectionRequest | None = None,
    ) -> GraphResponse:
        edges = [edge for edge in repository.graph_edges if edge.type in {"calls_api", "exposes_endpoint", "contains_call", "calls"}]
        if endpoint_id:
            edges = [edge for edge in edges if edge.source == endpoint_id or edge.target == endpoint_id]
        node_ids = self._node_ids_from_edges(edges)
        api_nodes = {
            node.id
            for node in repository.graph_nodes
            if node.type in {"endpoint", "api_call", "call_site"} or node.id in node_ids
        }
        return self._subgraph_by_ids(repository, "api-flow", request, api_nodes, edges)

    def function_flow(
        self,
        repository: RepositoryState,
        symbol_id: str | None = None,
        request: GraphProjectionRequest | None = None,
    ) -> GraphResponse:
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
        return self._subgraph_by_ids(repository, "function-flow", request, flow_nodes | node_ids, edges)

    def data_flow(
        self,
        repository: RepositoryState,
        symbol_id: str | None = None,
        request: GraphProjectionRequest | None = None,
    ) -> GraphResponse:
        edges = [edge for edge in repository.graph_edges if edge.type.startswith("dfg_")]
        if symbol_id:
            related = self._reachable_node_ids(edges, symbol_id, depth=3)
            edges = [edge for edge in edges if edge.source in related or edge.target in related]
        return self._from_edges(repository, "data-flow", request, edges)

    def _subgraph(
        self,
        repository: RepositoryState,
        view: str,
        request: GraphProjectionRequest | None,
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
        return self._project(repository, view, request, nodes, edges)

    def _from_edges(
        self,
        repository: RepositoryState,
        view: str,
        request: GraphProjectionRequest | None,
        edges: list[GraphEdgeDTO],
    ) -> GraphResponse:
        return self._subgraph_by_ids(repository, view, request, self._node_ids_from_edges(edges), edges)

    def _subgraph_by_ids(
        self,
        repository: RepositoryState,
        view: str,
        request: GraphProjectionRequest | None,
        node_ids: set[str],
        edges: list[GraphEdgeDTO],
    ) -> GraphResponse:
        nodes = [node for node in repository.graph_nodes if node.id in node_ids]
        visible = {node.id for node in nodes}
        filtered_edges = [edge for edge in edges if edge.source in visible and edge.target in visible]
        return self._project(repository, view, request, nodes, filtered_edges)

    def _project(
        self,
        repository: RepositoryState,
        view: str,
        request: GraphProjectionRequest | None,
        nodes: list[GraphNodeDTO],
        edges: list[GraphEdgeDTO],
    ) -> GraphResponse:
        requested = request or GraphProjectionRequest(max_nodes=self.max_nodes, max_edges=self.max_edges)
        if requested.index_version is not None and requested.index_version != repository.current_index_version:
            raise GraphProjectionVersionMismatch("Requested graph index version is not active")

        node_types = set(requested.node_types)
        edge_types = set(requested.edge_types)
        support_levels = set(requested.support_levels)
        filtered_nodes = [node for node in nodes if not node_types or node.type in node_types]
        visible = {node.id for node in filtered_nodes}
        filtered_edges = [
            edge
            for edge in edges
            if edge.source in visible
            and edge.target in visible
            and (not edge_types or edge.type in edge_types)
            and edge.confidence >= requested.min_confidence
            and (not support_levels or edge.evidence_level in support_levels)
        ]
        filtered_nodes, filtered_edges, ordered_ids, unsupported = self._bounded_traversal(
            filtered_nodes,
            filtered_edges,
            requested,
        )
        ordered_nodes = sorted(filtered_nodes, key=lambda node: (ordered_ids.get(node.id, len(ordered_ids)), node.type, node.id))
        ordered_edges = sorted(filtered_edges, key=lambda edge: (edge.type, edge.source, edge.target, -edge.confidence))
        available_nodes = len(ordered_nodes)
        available_edges = len(ordered_edges)
        node_limit = min(requested.max_nodes, self.max_nodes)
        edge_limit = min(requested.max_edges, self.max_edges)
        included_nodes = ordered_nodes[:node_limit]
        included_ids = {node.id for node in included_nodes}
        eligible_edges = [edge for edge in ordered_edges if edge.source in included_ids and edge.target in included_ids]
        included_edges = eligible_edges[:edge_limit]
        node_truncated = available_nodes > len(included_nodes)
        edge_budget_truncated = len(eligible_edges) > len(included_edges)
        truncated = node_truncated or edge_budget_truncated
        reason = "node_and_edge_budget" if node_truncated and edge_budget_truncated else "node_budget" if node_truncated else "edge_budget" if edge_budget_truncated else None
        unknown = ["requested_root_not_found"] if unsupported else []
        support = sorted({edge.evidence_level for edge in included_edges})
        can_expand = (node_truncated and requested.max_nodes < self.max_nodes) or (
            edge_budget_truncated and requested.max_edges < self.max_edges
        )

        return GraphResponse(
            nodes=included_nodes,
            edges=included_edges,
            repository_id=repository.id,
            index_version=repository.current_index_version,
            view=view,
            projection=requested,
            counts=GraphProjectionCounts(
                available_nodes=available_nodes,
                included_nodes=len(included_nodes),
                available_edges=available_edges,
                included_edges=len(included_edges),
            ),
            coverage=GraphProjectionCoverage(
                state="limited" if truncated or unsupported else "ready",
                measured={
                    "available_nodes": available_nodes,
                    "included_nodes": len(included_nodes),
                    "available_edges": available_edges,
                    "included_edges": len(included_edges),
                },
                unknown=unknown,
            ),
            truncation=GraphProjectionTruncation(truncated=truncated, reason=reason),
            unsupported_hops=unsupported,
            can_expand=can_expand,
            provenance=GraphProjectionProvenance(support_levels=support),
        )

    def _bounded_traversal(
        self,
        nodes: list[GraphNodeDTO],
        edges: list[GraphEdgeDTO],
        request: GraphProjectionRequest,
    ) -> tuple[list[GraphNodeDTO], list[GraphEdgeDTO], dict[str, int], list[str]]:
        node_by_id = {node.id: node for node in nodes}
        roots = [root for root in request.root_keys if root in node_by_id]
        unsupported = [root for root in request.root_keys if root not in node_by_id]
        if not request.root_keys:
            return nodes, edges, {}, []
        if not roots:
            return [], [], {}, unsupported

        ordered_ids: dict[str, int] = {}
        visited = set(roots)
        frontier = sorted(roots)
        for node_id in frontier:
            ordered_ids[node_id] = len(ordered_ids)
        for _ in range(request.max_depth):
            next_frontier: set[str] = set()
            for edge in edges:
                if request.direction in {"outgoing", "both"} and edge.source in frontier:
                    next_frontier.add(edge.target)
                if request.direction in {"incoming", "both"} and edge.target in frontier:
                    next_frontier.add(edge.source)
            next_frontier.difference_update(visited)
            frontier = sorted(next_frontier)
            for node_id in frontier:
                ordered_ids[node_id] = len(ordered_ids)
            visited.update(frontier)
            if not frontier:
                break
        traversed_nodes = [node for node in nodes if node.id in visited]
        traversed_edges = [edge for edge in edges if edge.source in visited and edge.target in visited]
        return traversed_nodes, traversed_edges, ordered_ids, unsupported

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
