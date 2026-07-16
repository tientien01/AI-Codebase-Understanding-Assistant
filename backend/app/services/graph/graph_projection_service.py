from __future__ import annotations

import json
import math
from pathlib import PurePosixPath
from urllib.parse import unquote

from app.schemas.graph import (
    GraphEdgeDTO,
    GraphNodeDTO,
    GraphNodeExpansionDTO,
    GraphProjectionCounts,
    GraphProjectionCoverage,
    GraphProjectionProvenance,
    GraphProjectionRequest,
    GraphProjectionTruncation,
    GraphResponse,
    GraphSeedDTO,
)
from app.services.index_models import RepositoryState


class GraphProjectionVersionMismatch(ValueError):
    """Raised when a client asks for a non-active compatibility index version."""


VALUE_TRACE_CONTEXT_PREFIX = "value-context:v1:"


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
        requested = request or GraphProjectionRequest(max_nodes=self.max_nodes, max_edges=self.max_edges)
        internal_edges = [edge for edge in repository.graph_edges if edge.type == "imports_internal"]
        detected_edges = [edge for edge in repository.graph_edges if edge.type == "imports"]
        if requested.dependency_scope == "adaptive":
            scope_used = "internal" if internal_edges else "detected"
        else:
            scope_used = requested.dependency_scope
        edges = internal_edges if scope_used == "internal" else detected_edges
        if file_path:
            file_node_ids = {node.id for node in repository.graph_nodes if node.file_path == file_path or node.scope_path == file_path}
            edges = [edge for edge in edges if edge.source in file_node_ids or edge.target in file_node_ids]
        node_ids = self._node_ids_from_edges(edges)
        nodes = [node for node in repository.graph_nodes if node.id in node_ids]
        visible = {node.id for node in nodes}
        edges = [edge for edge in edges if edge.source in visible and edge.target in visible]
        scope_unknown = "internal_dependency_resolution_unavailable" if scope_used == "internal" and not internal_edges else None
        if requested.projection_mode == "seeds":
            return self._dependency_seeds(repository, requested, nodes, edges, scope_used, scope_unknown)
        if requested.projection_mode == "neighbors":
            requested = requested.model_copy(update={"max_depth": 1})
        return self._project(
            repository,
            "dependencies",
            requested,
            nodes,
            edges,
            dependency_scope_used=scope_used,
            scope_unknown=scope_unknown,
        )

    def api_flow(
        self,
        repository: RepositoryState,
        endpoint_id: str | None = None,
        request: GraphProjectionRequest | None = None,
    ) -> GraphResponse:
        requested = request or GraphProjectionRequest(max_nodes=self.max_nodes, max_edges=self.max_edges)
        edges = [edge for edge in repository.graph_edges if edge.type in {"calls_api", "exposes_endpoint", "contains_call", "calls"}]
        if endpoint_id:
            edges = [edge for edge in edges if edge.source == endpoint_id or edge.target == endpoint_id]
        node_ids = self._node_ids_from_edges(edges)
        nodes = [
            node
            for node in repository.graph_nodes
            if node.type in {"endpoint", "api_call", "call_site"} or node.id in node_ids
        ]
        visible = {node.id for node in nodes}
        edges = [edge for edge in edges if edge.source in visible and edge.target in visible]
        if requested.projection_mode == "seeds":
            return self._request_flow_seeds(repository, requested, nodes, edges)
        if requested.projection_mode == "neighbors":
            requested = requested.model_copy(update={"max_depth": 1})
        return self._project(repository, "api-flow", requested, nodes, edges)

    def function_flow(
        self,
        repository: RepositoryState,
        symbol_id: str | None = None,
        request: GraphProjectionRequest | None = None,
    ) -> GraphResponse:
        requested = request or GraphProjectionRequest(max_nodes=self.max_nodes, max_edges=self.max_edges)
        # Call Flow is a semantic callable projection. Technical call-site and CFG
        # nodes remain in the canonical graph, but do not consume the default UI
        # budget. Direct resolved and classified non-repository calls retain their
        # original edge provenance and source metadata.
        call_edge_types = {
            "calls",
            "calls_builtin",
            "calls_stdlib",
            "calls_framework",
            "calls_external",
            "calls_unresolved",
        }
        edges = [edge for edge in repository.graph_edges if edge.type in call_edge_types]
        if symbol_id:
            related = self._reachable_node_ids(edges, symbol_id, depth=2)
            edges = [edge for edge in edges if edge.source in related or edge.target in related]
        node_ids = self._node_ids_from_edges(edges)
        nodes = [
            node
            for node in repository.graph_nodes
            if node.id in node_ids or node.type in {"function", "method"}
        ]
        visible = {node.id for node in nodes}
        edges = [edge for edge in edges if edge.source in visible and edge.target in visible]
        if requested.projection_mode == "seeds":
            return self._call_flow_seeds(repository, requested, nodes, edges)
        if requested.projection_mode == "neighbors":
            requested = requested.model_copy(update={"max_depth": 1})
        return self._project(repository, "function-flow", requested, nodes, edges)

    def data_flow(
        self,
        repository: RepositoryState,
        symbol_id: str | None = None,
        request: GraphProjectionRequest | None = None,
    ) -> GraphResponse:
        requested = request or GraphProjectionRequest(max_nodes=self.max_nodes, max_edges=self.max_edges)
        edges = [edge for edge in repository.graph_edges if edge.type.startswith("dfg_")]
        nodes = [node for node in repository.graph_nodes if node.type == "dfg_node"]
        if symbol_id:
            related = self._reachable_node_ids(edges, symbol_id, depth=3)
            edges = [edge for edge in edges if edge.source in related or edge.target in related]
            nodes = [node for node in nodes if node.id in related]
        visible = {node.id for node in nodes}
        edges = [edge for edge in edges if edge.source in visible and edge.target in visible]
        if requested.projection_mode == "seeds":
            return self._data_flow_seeds(repository, requested, nodes, edges)
        if requested.projection_mode == "neighbors":
            requested = requested.model_copy(update={"max_depth": 1})
        return self._project(repository, "data-flow", requested, nodes, edges)

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
        *,
        dependency_scope_used: str | None = None,
        scope_unknown: str | None = None,
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
        expansion_edges = list(filtered_edges)
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
        if requested.projection_mode == "neighbors" and len(requested.root_keys) == 1:
            root_key = requested.root_keys[0]
            root_node = next((node for node in ordered_nodes if node.id == root_key), None)
            neighbors = [node for node in ordered_nodes if node.id != root_key]
            page_size = max(0, node_limit - (1 if root_node else 0))
            page = neighbors[requested.neighbor_offset : requested.neighbor_offset + page_size]
            included_nodes = ([root_node] if root_node else []) + page
        else:
            included_nodes = ordered_nodes[:node_limit]
        included_ids = {node.id for node in included_nodes}
        eligible_edges = [edge for edge in ordered_edges if edge.source in included_ids and edge.target in included_ids]
        included_edges = eligible_edges[:edge_limit]
        if requested.projection_mode == "neighbors" and len(requested.root_keys) == 1:
            available_neighbors = available_nodes - (1 if root_node else 0)
            included_neighbor_count = len(included_nodes) - (1 if root_node else 0)
            node_truncated = available_neighbors > requested.neighbor_offset + included_neighbor_count
        else:
            node_truncated = available_nodes > len(included_nodes)
        edge_budget_truncated = len(eligible_edges) > len(included_edges)
        truncated = node_truncated or edge_budget_truncated
        reason = "node_and_edge_budget" if node_truncated and edge_budget_truncated else "node_budget" if node_truncated else "edge_budget" if edge_budget_truncated else None
        unknown = ["requested_root_not_found"] if unsupported else []
        if scope_unknown:
            unknown.append(scope_unknown)
        support = sorted({edge.evidence_level for edge in included_edges})
        can_expand = (node_truncated and requested.max_nodes < self.max_nodes) or (
            edge_budget_truncated and requested.max_edges < self.max_edges
        )

        expansion = self._expansion_metadata(
            requested,
            expansion_edges,
            included_nodes,
            limited=truncated or bool(unsupported) or bool(scope_unknown),
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
                state="limited" if truncated or unsupported or scope_unknown else "ready",
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
            dependency_scope_used=dependency_scope_used,
            expansion=expansion,
        )

    def _dependency_seeds(
        self,
        repository: RepositoryState,
        request: GraphProjectionRequest,
        nodes: list[GraphNodeDTO],
        edges: list[GraphEdgeDTO],
        scope_used: str,
        scope_unknown: str | None,
    ) -> GraphResponse:
        if request.index_version is not None and request.index_version != repository.current_index_version:
            raise GraphProjectionVersionMismatch("Requested graph index version is not active")

        filtered_nodes, filtered_edges = self._filter_projection(nodes, edges, request)
        node_by_id = {node.id: node for node in filtered_nodes}
        incoming = {node_id: 0 for node_id in node_by_id}
        outgoing = {node_id: 0 for node_id in node_by_id}
        for edge in filtered_edges:
            outgoing[edge.source] += 1
            incoming[edge.target] += 1

        endpoint_files = {endpoint.file_path for endpoint in repository.endpoints}
        degrees = sorted(incoming[node_id] + outgoing[node_id] for node_id in node_by_id)
        threshold_index = max(0, math.ceil(len(degrees) * 0.75) - 1) if degrees else 0
        degree_threshold = degrees[threshold_index] if degrees else 0
        qualification_threshold = max(1, degree_threshold) if len(degrees) <= 3 else max(2, degree_threshold)
        ranked: list[tuple[int, str, str, list[str]]] = []
        for node in filtered_nodes:
            reasons: list[str] = []
            role = (node.role or "").lower()
            file_name = PurePosixPath(node.file_path or "").name.lower()
            if "entrypoint" in role or file_name in {"main.py", "app.py", "server.py", "main.ts", "main.tsx"}:
                reasons.append("application_entrypoint")
            if node.file_path in endpoint_files:
                reasons.append("endpoint_owner")
            if incoming[node.id] and outgoing[node.id]:
                reasons.append("dependency_bridge")
            if incoming[node.id] >= max(2, degree_threshold):
                reasons.append("many_dependents")
            if outgoing[node.id] >= max(2, degree_threshold):
                reasons.append("many_dependencies")
            strong_role = "application_entrypoint" in reasons or "endpoint_owner" in reasons
            degree = incoming[node.id] + outgoing[node.id]
            if not strong_role and degree < qualification_threshold:
                continue
            if not reasons:
                reasons.append("graph_region_representative")
            score = (
                (8 if "application_entrypoint" in reasons else 0)
                + (6 if "endpoint_owner" in reasons else 0)
                + (4 if "dependency_bridge" in reasons else 0)
                + incoming[node.id] * 2
                + outgoing[node.id]
            )
            ranked.append((score, self._graph_region(node), node.id, reasons))

        ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
        limit = min(request.seed_limit, request.max_nodes, self.max_nodes)
        selected: list[tuple[int, str, str, list[str]]] = []
        selected_ids: set[str] = set()
        # First represent distinct graph regions, then fill remaining capacity by evidence-backed rank.
        for item in ranked:
            if item[1] in {selected_item[1] for selected_item in selected}:
                continue
            selected.append(item)
            selected_ids.add(item[2])
            if len(selected) >= limit:
                break
        if len(selected) < limit:
            for item in ranked:
                if item[2] in selected_ids:
                    continue
                selected.append(item)
                selected_ids.add(item[2])
                if len(selected) >= limit:
                    break

        included_nodes = [node_by_id[item[2]] for item in selected]
        included_edges: list[GraphEdgeDTO] = []
        seeds = [
            GraphSeedDTO(
                node_id=item[2],
                reason_codes=item[3],
                incoming_available=incoming[item[2]],
                outgoing_available=outgoing[item[2]],
            )
            for item in selected
        ]
        unknown = [scope_unknown] if scope_unknown else []
        support = sorted({edge.evidence_level for edge in filtered_edges})
        return GraphResponse(
            nodes=included_nodes,
            edges=included_edges,
            repository_id=repository.id,
            index_version=repository.current_index_version,
            view="dependencies",
            projection=request,
            counts=GraphProjectionCounts(
                available_nodes=len(filtered_nodes),
                included_nodes=len(included_nodes),
                available_edges=len(filtered_edges),
                included_edges=len(included_edges),
            ),
            coverage=GraphProjectionCoverage(
                state="limited" if scope_unknown else "ready",
                measured={
                    "eligible_nodes": len(filtered_nodes),
                    "qualifying_starting_points": len(ranked),
                    "selected_starting_points": len(included_nodes),
                },
                unknown=unknown,
            ),
            truncation=GraphProjectionTruncation(truncated=False),
            provenance=GraphProjectionProvenance(support_levels=support),
            dependency_scope_used=scope_used,
            seed_strategy="dependency-starting-points/v1",
            seeds=seeds,
            additional_starting_points=max(0, len(ranked) - len(selected)),
        )

    def _request_flow_seeds(
        self,
        repository: RepositoryState,
        request: GraphProjectionRequest,
        nodes: list[GraphNodeDTO],
        edges: list[GraphEdgeDTO],
    ) -> GraphResponse:
        if request.index_version is not None and request.index_version != repository.current_index_version:
            raise GraphProjectionVersionMismatch("Requested graph index version is not active")

        edge_types = set(request.edge_types)
        support_levels = set(request.support_levels)
        eligible_edges = [
            edge
            for edge in edges
            if (not edge_types or edge.type in edge_types)
            and edge.confidence >= request.min_confidence
            and (not support_levels or edge.evidence_level in support_levels)
        ]
        node_by_id = {node.id: node for node in nodes}
        all_candidates = [node for node in nodes if node.type in {"endpoint", "api_call"}]
        requested_entry_types = set(request.node_types) & {"endpoint", "api_call"}
        if not requested_entry_types:
            requested_entry_types = {"endpoint", "api_call"}
        candidates = [node for node in all_candidates if node.type in requested_entry_types]
        incoming: dict[str, list[GraphEdgeDTO]] = {node.id: [] for node in all_candidates}
        outgoing: dict[str, list[GraphEdgeDTO]] = {node.id: [] for node in all_candidates}
        for edge in eligible_edges:
            if edge.source in outgoing:
                outgoing[edge.source].append(edge)
            if edge.target in incoming:
                incoming[edge.target].append(edge)

        ranked: list[tuple[int, int, str, list[str]]] = []
        for node in candidates:
            reasons = ["server_endpoint"] if node.type == "endpoint" else ["client_api_call"]
            if node.type == "endpoint":
                resolved = any(edge.type == "exposes_endpoint" for edge in outgoing[node.id])
                reasons.append("handler_resolved" if resolved else "handler_unresolved")
                priority = 0 if resolved else 2
            else:
                matched = any(edge.type == "calls_api" for edge in outgoing[node.id])
                reasons.append("client_call_matched" if matched else "client_call_unmatched")
                priority = 1 if matched else 3
            ranked.append((priority, 0 if node.type == "endpoint" else 1, node.id, reasons))

        ranked.sort(key=lambda item: (item[0], item[1], node_by_id[item[2]].label.lower(), item[2]))
        limit = min(request.seed_limit, request.max_nodes, self.max_nodes)
        selected = ranked[request.neighbor_offset : request.neighbor_offset + limit]
        selected_nodes = [node_by_id[item[2]] for item in selected]
        seeds = [
            GraphSeedDTO(
                node_id=item[2],
                reason_codes=item[3],
                incoming_available=len(incoming[item[2]]),
                outgoing_available=len(outgoing[item[2]]),
            )
            for item in selected
        ]
        endpoint_count = sum(node.type == "endpoint" for node in all_candidates)
        client_call_count = sum(node.type == "api_call" for node in all_candidates)
        resolved_handlers = sum(
            node.type == "endpoint" and any(edge.type == "exposes_endpoint" for edge in outgoing[node.id])
            for node in all_candidates
        )
        matched_clients = sum(
            node.type == "api_call" and any(edge.type == "calls_api" for edge in outgoing[node.id])
            for node in all_candidates
        )
        unknown: list[str] = []
        if endpoint_count > resolved_handlers:
            unknown.append("endpoint_handler_unresolved")
        if client_call_count > matched_clients:
            unknown.append("client_call_unmatched")
        return GraphResponse(
            nodes=selected_nodes,
            edges=[],
            repository_id=repository.id,
            index_version=repository.current_index_version,
            view="api-flow",
            projection=request,
            counts=GraphProjectionCounts(
                available_nodes=len(candidates),
                included_nodes=len(selected_nodes),
                available_edges=len(eligible_edges),
                included_edges=0,
            ),
            coverage=GraphProjectionCoverage(
                state="limited" if unknown else "ready",
                measured={
                    "indexed_endpoints": endpoint_count,
                    "client_api_calls": client_call_count,
                    "resolved_handlers": resolved_handlers,
                    "matched_client_calls": matched_clients,
                },
                unknown=unknown,
            ),
            truncation=GraphProjectionTruncation(truncated=False),
            provenance=GraphProjectionProvenance(
                support_levels=sorted({edge.evidence_level for edge in eligible_edges})
            ),
            seed_strategy="request-entry-points/v1",
            seeds=seeds,
            additional_starting_points=max(0, len(ranked) - request.neighbor_offset - len(selected)),
        )

    def _call_flow_seeds(
        self,
        repository: RepositoryState,
        request: GraphProjectionRequest,
        nodes: list[GraphNodeDTO],
        edges: list[GraphEdgeDTO],
    ) -> GraphResponse:
        if request.index_version is not None and request.index_version != repository.current_index_version:
            raise GraphProjectionVersionMismatch("Requested graph index version is not active")

        edge_types = set(request.edge_types)
        support_levels = set(request.support_levels)
        eligible_edges = [
            edge
            for edge in edges
            if (not edge_types or edge.type in edge_types)
            and edge.confidence >= request.min_confidence
            and (not support_levels or edge.evidence_level in support_levels)
        ]
        callable_nodes = [node for node in nodes if node.type in {"function", "method"}]
        node_by_id = {node.id: node for node in callable_nodes}
        incoming: dict[str, list[GraphEdgeDTO]] = {node.id: [] for node in callable_nodes}
        outgoing: dict[str, list[GraphEdgeDTO]] = {node.id: [] for node in callable_nodes}
        for edge in eligible_edges:
            if edge.source in outgoing:
                outgoing[edge.source].append(edge)
            if edge.target in incoming:
                incoming[edge.target].append(edge)

        endpoint_files = {endpoint.file_path for endpoint in repository.endpoints}
        ranked: list[tuple[int, str, str, list[str]]] = []
        for node in callable_nodes:
            direct_in = len(incoming[node.id])
            direct_out = len(outgoing[node.id])
            reasons: list[str] = []
            if node.file_path in endpoint_files:
                reasons.append("endpoint_handler")
            if direct_in >= 2:
                reasons.append("many_callers")
            if direct_out >= 2:
                reasons.append("many_callees")
            if any(edge.source == node.id and edge.target == node.id for edge in outgoing[node.id]):
                reasons.append("direct_recursion")
            if not direct_in:
                reasons.append("no_supported_internal_caller")
            if not reasons:
                reasons.append("indexed_callable")
            score = (
                (10 if "endpoint_handler" in reasons else 0)
                + (8 if "direct_recursion" in reasons else 0)
                + direct_in * 2
                + direct_out
            )
            ranked.append((score, node.label.lower(), node.id, reasons))

        ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
        limit = min(request.seed_limit, request.max_nodes, self.max_nodes)
        selected = ranked[request.neighbor_offset : request.neighbor_offset + limit]
        selected_nodes = [node_by_id[item[2]] for item in selected]
        seeds = [
            GraphSeedDTO(
                node_id=item[2],
                reason_codes=item[3],
                incoming_available=len(incoming[item[2]]),
                outgoing_available=len(outgoing[item[2]]),
            )
            for item in selected
        ]
        resolved_edges = [edge for edge in eligible_edges if edge.type == "calls"]
        unresolved_edges = [edge for edge in eligible_edges if edge.type == "calls_unresolved"]
        external_edges = [
            edge
            for edge in eligible_edges
            if edge.type in {"calls_builtin", "calls_stdlib", "calls_framework", "calls_external"}
        ]
        recursive_nodes = {
            edge.source for edge in eligible_edges if edge.source == edge.target and edge.source in node_by_id
        }
        support = sorted({edge.evidence_level for edge in eligible_edges})
        unknown = ["unresolved_call_targets"] if unresolved_edges else []
        return GraphResponse(
            nodes=selected_nodes,
            edges=[],
            repository_id=repository.id,
            index_version=repository.current_index_version,
            view="function-flow",
            projection=request,
            counts=GraphProjectionCounts(
                available_nodes=len(callable_nodes),
                included_nodes=len(selected_nodes),
                available_edges=len(eligible_edges),
                included_edges=0,
            ),
            coverage=GraphProjectionCoverage(
                state="limited" if unknown else "ready",
                measured={
                    "indexed_callables": len(callable_nodes),
                    "resolved_call_relations": len(resolved_edges),
                    "external_call_relations": len(external_edges),
                    "unresolved_call_relations": len(unresolved_edges),
                    "direct_recursive_callables": len(recursive_nodes),
                },
                unknown=unknown,
            ),
            truncation=GraphProjectionTruncation(truncated=False),
            provenance=GraphProjectionProvenance(support_levels=support),
            seed_strategy="callable-starting-points/v1",
            seeds=seeds,
            additional_starting_points=max(0, len(ranked) - request.neighbor_offset - len(selected)),
        )

    def _data_flow_seeds(
        self,
        repository: RepositoryState,
        request: GraphProjectionRequest,
        nodes: list[GraphNodeDTO],
        edges: list[GraphEdgeDTO],
    ) -> GraphResponse:
        """Return stable value candidates without projecting a repository-wide DFG.

        The compatibility analyzer currently proves only intraprocedural parameter,
        definition and use roles. Seed ranking therefore uses those stored roles and
        direct graph degree only; it does not infer transformations or call binding.
        """
        if request.index_version is not None and request.index_version != repository.current_index_version:
            raise GraphProjectionVersionMismatch("Requested graph index version is not active")

        all_nodes, eligible_edges = self._filter_projection(nodes, edges, request)
        filtered_nodes = [
            node
            for node in all_nodes
            if any(self._value_context_matches(node, root) for root in request.root_keys)
        ]
        node_by_id = {node.id: node for node in filtered_nodes}
        incoming: dict[str, list[GraphEdgeDTO]] = {node.id: [] for node in filtered_nodes}
        outgoing: dict[str, list[GraphEdgeDTO]] = {node.id: [] for node in filtered_nodes}
        for edge in eligible_edges:
            if edge.source in outgoing:
                outgoing[edge.source].append(edge)
            if edge.target in incoming:
                incoming[edge.target].append(edge)
        contextual_edges = [
            edge
            for edge in eligible_edges
            if edge.source in node_by_id or edge.target in node_by_id
        ]

        role_priority = {"parameter": 0, "definition": 1, "use": 2}
        ranked: list[tuple[int, int, str, int, str, list[str]]] = []
        for node in filtered_nodes:
            role = (node.role or "unresolved").lower()
            reasons = [f"value_{role}"] if role in role_priority else ["value_role_unresolved"]
            direct_in = len(incoming[node.id])
            direct_out = len(outgoing[node.id])
            if direct_in:
                reasons.append("has_supported_origin")
            if direct_out:
                reasons.append("has_supported_use")
            if direct_out >= 2:
                reasons.append("multiple_supported_uses")
            ranked.append(
                (
                    role_priority.get(role, 3),
                    -(direct_in + direct_out),
                    (node.file_path or node.scope_path or "").lower(),
                    node.start_line or 0,
                    node.id,
                    reasons,
                )
            )

        ranked.sort(key=lambda item: item[:5])
        limit = min(request.seed_limit, request.max_nodes, self.max_nodes)
        selected = ranked[request.neighbor_offset : request.neighbor_offset + limit]
        selected_nodes = [node_by_id[item[4]] for item in selected]
        seeds = [
            GraphSeedDTO(
                node_id=item[4],
                reason_codes=item[5],
                incoming_available=len(incoming[item[4]]),
                outgoing_available=len(outgoing[item[4]]),
            )
            for item in selected
        ]
        role_counts = {
            role: sum((node.role or "").lower() == role for node in filtered_nodes)
            for role in ("parameter", "definition", "use")
        }
        support = sorted({edge.evidence_level for edge in contextual_edges})
        interprocedural_edges = {
            "dfg_argument_to_parameter",
            "dfg_return_to_call_result",
        }
        has_interprocedural_support = any(edge.type in interprocedural_edges for edge in eligible_edges)
        unknown = (
            ["interprocedural_value_flow_limited" if has_interprocedural_support else "interprocedural_value_flow_unavailable"]
            if filtered_nodes
            else []
        )
        return GraphResponse(
            nodes=selected_nodes,
            edges=[],
            repository_id=repository.id,
            index_version=repository.current_index_version,
            view="data-flow",
            projection=request,
            counts=GraphProjectionCounts(
                available_nodes=len(filtered_nodes),
                included_nodes=len(selected_nodes),
                available_edges=len(contextual_edges),
                included_edges=0,
            ),
            coverage=GraphProjectionCoverage(
                state="limited" if unknown else "ready",
                measured={
                    "indexed_value_nodes": len(filtered_nodes),
                    "parameter_nodes": role_counts["parameter"],
                    "definition_nodes": role_counts["definition"],
                    "use_nodes": role_counts["use"],
                    "supported_value_relations": len(contextual_edges),
                },
                unknown=unknown,
            ),
            truncation=GraphProjectionTruncation(truncated=False),
            provenance=GraphProjectionProvenance(support_levels=support),
            seed_strategy="value-context-starting-points/v1" if request.root_keys else "value-context-required/v1",
            seeds=seeds,
            additional_starting_points=max(0, len(ranked) - request.neighbor_offset - len(selected)),
        )

    def _value_context_matches(self, node: GraphNodeDTO, root: str) -> bool:
        if root == node.id:
            return True
        if not root.startswith(VALUE_TRACE_CONTEXT_PREFIX):
            return False
        try:
            payload = json.loads(unquote(root.removeprefix(VALUE_TRACE_CONTEXT_PREFIX)))
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
        if not isinstance(payload, dict) or payload.get("f") != node.file_path:
            return False

        line = node.start_line or 0
        if payload.get("k") == "token":
            value = payload.get("v")
            requested_line = payload.get("l")
            node_value = node.label.split(":", 1)[-1].strip()
            return (
                isinstance(value, str)
                and isinstance(requested_line, int)
                and requested_line == line
                and value == node_value
            )
        if payload.get("k") == "scope":
            start = payload.get("s")
            end = payload.get("e", start)
            return (
                isinstance(start, int)
                and isinstance(end, int)
                and start > 0
                and start <= line <= end
            )
        return False

    def _filter_projection(
        self,
        nodes: list[GraphNodeDTO],
        edges: list[GraphEdgeDTO],
        request: GraphProjectionRequest,
    ) -> tuple[list[GraphNodeDTO], list[GraphEdgeDTO]]:
        node_types = set(request.node_types)
        edge_types = set(request.edge_types)
        support_levels = set(request.support_levels)
        filtered_nodes = [node for node in nodes if not node_types or node.type in node_types]
        visible = {node.id for node in filtered_nodes}
        filtered_edges = [
            edge
            for edge in edges
            if edge.source in visible
            and edge.target in visible
            and (not edge_types or edge.type in edge_types)
            and edge.confidence >= request.min_confidence
            and (not support_levels or edge.evidence_level in support_levels)
        ]
        return filtered_nodes, filtered_edges

    def _expansion_metadata(
        self,
        request: GraphProjectionRequest,
        edges: list[GraphEdgeDTO],
        included_nodes: list[GraphNodeDTO],
        *,
        limited: bool,
    ) -> GraphNodeExpansionDTO | None:
        if request.projection_mode != "neighbors" or len(request.root_keys) != 1:
            return None
        root = request.root_keys[0]
        incoming = {edge.source for edge in edges if edge.target == root}
        outgoing = {edge.target for edge in edges if edge.source == root}
        if request.direction == "incoming":
            available = incoming
        elif request.direction == "outgoing":
            available = outgoing
        else:
            available = incoming | outgoing
        included = {node.id for node in included_nodes}
        included_neighbors = len((included - {root}) & available)
        remaining = max(0, len(available) - request.neighbor_offset - included_neighbors)
        next_offset = request.neighbor_offset + included_neighbors if remaining else None
        return GraphNodeExpansionDTO(
            root_key=root,
            incoming_available=len(incoming),
            outgoing_available=len(outgoing),
            included_neighbors=included_neighbors,
            remaining_neighbors=remaining,
            next_neighbor_offset=next_offset,
            leaf=not available,
            limited=limited or remaining > 0,
        )

    def _graph_region(self, node: GraphNodeDTO) -> str:
        path = (node.file_path or node.scope_path or node.id).replace("\\", "/")
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 2 and parts[0].lower() in {"src", "app", "backend", "frontend", "packages", "apps"}:
            return "/".join(parts[:2]).lower()
        return (parts[0] if parts else node.type).lower()

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
