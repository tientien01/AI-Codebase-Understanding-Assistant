from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi import HTTPException

from app.api.v1.routes.graph import run_projection
from app.schemas.graph import GraphEdgeDTO, GraphNodeDTO, GraphProjectionRequest
from app.services.graph.graph_projection_service import GraphProjectionService, GraphProjectionVersionMismatch
from app.services.index_models import RepositoryState


def test_projection_enforces_budgets_discloses_truncation_and_never_returns_dangling_edges(tmp_path: Path) -> None:
    repository = chain_repository(tmp_path, node_count=300)

    result = GraphProjectionService().all(
        repository,
        GraphProjectionRequest(index_version=7, max_nodes=40, max_edges=12),
    )

    assert result.repository_id == "repo-graph"
    assert result.index_version == 7
    assert result.counts.available_nodes == 300
    assert result.counts.included_nodes == 40
    assert result.counts.available_edges == 299
    assert result.counts.included_edges == 12
    assert result.truncation.model_dump() == {
        "truncated": True,
        "reason": "node_and_edge_budget",
        "continuation_token": None,
    }
    assert result.coverage.state == "limited"
    assert result.can_expand is True
    visible = {node.id for node in result.nodes}
    assert all(edge.source in visible and edge.target in visible for edge in result.edges)


def test_projection_filters_support_and_traverses_in_the_declared_direction(tmp_path: Path) -> None:
    repository = chain_repository(tmp_path, node_count=8)
    repository.graph_edges[2].evidence_level = "inferred"
    repository.graph_edges[3].confidence = 0.4

    result = GraphProjectionService().all(
        repository,
        GraphProjectionRequest(
            root_keys=["node-2"],
            direction="outgoing",
            max_depth=3,
            min_confidence=0.5,
            support_levels=["deep"],
        ),
    )

    assert [node.id for node in result.nodes] == ["node-2"]
    assert result.edges == []
    assert result.truncation.truncated is False
    assert result.provenance.support_levels == []


def test_projection_incoming_traversal_stops_at_the_requested_depth(tmp_path: Path) -> None:
    result = GraphProjectionService().all(
        chain_repository(tmp_path, node_count=8),
        GraphProjectionRequest(root_keys=["node-4"], direction="incoming", max_depth=2),
    )

    assert {node.id for node in result.nodes} == {"node-2", "node-3", "node-4"}
    assert {(edge.source, edge.target) for edge in result.edges} == {
        ("node-2", "node-3"),
        ("node-3", "node-4"),
    }


def test_projection_reports_missing_roots_without_falling_back_to_an_unrelated_graph(tmp_path: Path) -> None:
    result = GraphProjectionService().all(
        chain_repository(tmp_path, node_count=5),
        GraphProjectionRequest(root_keys=["missing-root"]),
    )

    assert result.nodes == []
    assert result.edges == []
    assert result.coverage.state == "limited"
    assert result.coverage.unknown == ["requested_root_not_found"]
    assert result.unsupported_hops == ["missing-root"]


def test_projection_order_is_deterministic_for_large_reversed_inputs(tmp_path: Path) -> None:
    repository = chain_repository(tmp_path, node_count=1_000)
    reversed_repository = chain_repository(tmp_path, node_count=1_000)
    reversed_repository.graph_nodes.reverse()
    reversed_repository.graph_edges.reverse()
    request = GraphProjectionRequest(max_nodes=220, max_edges=520)
    service = GraphProjectionService()

    first = service.all(repository, request)
    second = service.all(reversed_repository, request)

    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [(edge.source, edge.target, edge.type) for edge in first.edges] == [
        (edge.source, edge.target, edge.type) for edge in second.edges
    ]
    assert first.counts.available_nodes == 1_000
    assert first.counts.included_nodes == 220


def test_projection_rejects_a_non_active_compatibility_index_version(tmp_path: Path) -> None:
    with pytest.raises(GraphProjectionVersionMismatch, match="not active"):
        GraphProjectionService().all(
            chain_repository(tmp_path, node_count=2),
            GraphProjectionRequest(index_version=6),
        )


def test_route_maps_version_mismatch_to_a_safe_non_retryable_conflict() -> None:
    def mismatch():
        raise GraphProjectionVersionMismatch("Requested graph index version is not active")

    with pytest.raises(HTTPException) as captured:
        run_projection(mismatch)

    assert captured.value.status_code == 409
    assert captured.value.detail == {
        "code": "GRAPH_INDEX_VERSION_NOT_ACTIVE",
        "message": "Requested graph index version is not active",
        "retryable": False,
    }


def test_dependency_seeds_are_adaptive_reasoned_and_prefer_resolved_internal_edges(tmp_path: Path) -> None:
    repository = dependency_repository(
        tmp_path,
        paths=["src/main.py", "src/service.py", "src/model.py"],
        relations=[(0, 1), (1, 2)],
    )
    repository.graph_nodes[0].role = "Entrypoint"

    result = GraphProjectionService().dependencies(
        repository,
        request=GraphProjectionRequest(
            projection_mode="seeds",
            dependency_scope="adaptive",
            node_types=["file"],
            edge_types=["imports_internal"],
            seed_limit=12,
        ),
    )

    assert result.dependency_scope_used == "internal"
    assert result.seed_strategy == "dependency-starting-points/v1"
    assert [node.file_path for node in result.nodes] == ["src/main.py", "src/service.py"]
    assert result.seeds[0].reason_codes == ["application_entrypoint"]
    assert "dependency_bridge" in result.seeds[1].reason_codes
    assert result.additional_starting_points == 0
    assert result.counts.available_nodes == 3
    assert result.counts.available_edges == 2
    assert result.counts.included_edges == 0
    assert result.edges == []
    assert result.truncation.truncated is False


def test_dependency_seed_selection_caps_many_candidates_with_region_diversity_and_stable_order(tmp_path: Path) -> None:
    paths = [f"src/area-{index % 4}/node-{index}.py" for index in range(20)]
    relations = [(index, (index + 1) % len(paths)) for index in range(len(paths))]
    repository = dependency_repository(tmp_path, paths=paths, relations=relations)
    reversed_repository = dependency_repository(tmp_path, paths=paths, relations=relations)
    reversed_repository.graph_nodes.reverse()
    reversed_repository.graph_edges.reverse()
    request = GraphProjectionRequest(
        projection_mode="seeds",
        dependency_scope="internal",
        node_types=["file"],
        edge_types=["imports_internal"],
        seed_limit=5,
    )

    first = GraphProjectionService().dependencies(repository, request=request)
    second = GraphProjectionService().dependencies(reversed_repository, request=request)

    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert len(first.nodes) == 5
    assert len({Path(node.file_path or "").parts[1] for node in first.nodes[:4]}) == 4
    assert first.additional_starting_points == 15


def test_dependency_neighbor_expansion_is_one_hop_and_discloses_remaining_neighbors(tmp_path: Path) -> None:
    repository = dependency_repository(
        tmp_path,
        paths=["src/a.py", "src/b.py", "src/c.py", "src/d.py"],
        relations=[(0, 1), (1, 2), (1, 3)],
    )

    result = GraphProjectionService().dependencies(
        repository,
        request=GraphProjectionRequest(
            projection_mode="neighbors",
            dependency_scope="internal",
            root_keys=["node-1"],
            node_types=["file"],
            edge_types=["imports_internal"],
            direction="both",
            max_depth=6,
            max_nodes=3,
        ),
    )

    assert result.projection.max_depth == 1
    assert result.expansion is not None
    assert result.expansion.root_key == "node-1"
    assert result.expansion.incoming_available == 1
    assert result.expansion.outgoing_available == 2
    assert result.expansion.included_neighbors == 2
    assert result.expansion.remaining_neighbors == 1
    assert result.expansion.next_neighbor_offset == 2
    assert result.expansion.leaf is False
    assert result.expansion.limited is True
    assert all(edge.source in {node.id for node in result.nodes} for edge in result.edges)
    assert all(edge.target in {node.id for node in result.nodes} for edge in result.edges)

    final_page = GraphProjectionService().dependencies(
        repository,
        request=GraphProjectionRequest(
            projection_mode="neighbors",
            dependency_scope="internal",
            root_keys=["node-1"],
            node_types=["file"],
            edge_types=["imports_internal"],
            direction="both",
            max_nodes=3,
            neighbor_offset=2,
        ),
    )
    assert final_page.expansion is not None
    assert final_page.expansion.included_neighbors == 1
    assert final_page.expansion.remaining_neighbors == 0
    assert final_page.expansion.next_neighbor_offset is None
    assert final_page.expansion.limited is False
    assert final_page.coverage.state == "ready"


def test_adaptive_dependency_scope_falls_back_to_detected_imports_without_external_claim(tmp_path: Path) -> None:
    repository = dependency_repository(
        tmp_path,
        paths=["src/client.ts", "react"],
        relations=[(0, 1)],
        relation_type="imports",
        node_types=["file", "module"],
    )

    result = GraphProjectionService().dependencies(
        repository,
        request=GraphProjectionRequest(
            projection_mode="seeds",
            dependency_scope="adaptive",
            node_types=["file", "module"],
            edge_types=["imports"],
        ),
    )

    assert result.dependency_scope_used == "detected"
    assert result.coverage.state == "ready"
    assert result.coverage.unknown == []


def test_request_flow_seeds_are_entry_points_with_resolution_status(tmp_path: Path) -> None:
    repository = request_flow_repository(tmp_path)

    result = GraphProjectionService().api_flow(
        repository,
        request=GraphProjectionRequest(
            projection_mode="seeds",
            node_types=["endpoint", "api_call"],
            edge_types=["calls_api", "exposes_endpoint", "calls"],
            seed_limit=12,
        ),
    )

    assert result.seed_strategy == "request-entry-points/v1"
    assert [node.id for node in result.nodes] == ["endpoint", "client-call", "unmatched-client"]
    assert result.edges == []
    assert [seed.reason_codes for seed in result.seeds] == [
        ["server_endpoint", "handler_resolved"],
        ["client_api_call", "client_call_matched"],
        ["client_api_call", "client_call_unmatched"],
    ]
    assert result.coverage.measured == {
        "indexed_endpoints": 1,
        "client_api_calls": 2,
        "resolved_handlers": 1,
        "matched_client_calls": 1,
    }
    assert result.coverage.state == "limited"
    assert result.coverage.unknown == ["client_call_unmatched"]


def test_request_flow_neighbor_expansion_is_one_hop_and_suppresses_call_sites(tmp_path: Path) -> None:
    result = GraphProjectionService().api_flow(
        request_flow_repository(tmp_path),
        request=GraphProjectionRequest(
            projection_mode="neighbors",
            root_keys=["endpoint"],
            node_types=["endpoint", "api_call", "function", "method"],
            edge_types=["calls_api", "exposes_endpoint", "calls"],
            direction="both",
            max_depth=5,
            max_nodes=10,
            max_edges=24,
        ),
    )

    assert result.projection.max_depth == 1
    assert {node.id for node in result.nodes} == {"endpoint", "client-call", "handler"}
    assert "call-site" not in {node.id for node in result.nodes}
    assert {(edge.source, edge.target, edge.type) for edge in result.edges} == {
        ("client-call", "endpoint", "calls_api"),
        ("endpoint", "handler", "exposes_endpoint"),
    }
    assert result.expansion is not None
    assert result.expansion.incoming_available == 1
    assert result.expansion.outgoing_available == 1
    assert result.expansion.included_neighbors == 2
    assert result.expansion.leaf is False


def test_request_flow_seed_pages_cover_large_entry_sets_without_overlap(tmp_path: Path) -> None:
    repository = request_flow_repository(tmp_path)
    repository.graph_nodes.extend(
        GraphNodeDTO(
            id=f"endpoint-{index:02d}",
            type="endpoint",
            label=f"GET /resource/{index:02d}",
            file_path=f"api/resource_{index:02d}.py",
        )
        for index in range(30)
    )
    service = GraphProjectionService()

    first = service.api_flow(
        repository,
        request=GraphProjectionRequest(
            projection_mode="seeds",
            node_types=["endpoint"],
            edge_types=["calls_api", "exposes_endpoint", "calls"],
            seed_limit=10,
            neighbor_offset=0,
        ),
    )
    second = service.api_flow(
        repository,
        request=GraphProjectionRequest(
            projection_mode="seeds",
            node_types=["endpoint"],
            edge_types=["calls_api", "exposes_endpoint", "calls"],
            seed_limit=10,
            neighbor_offset=10,
        ),
    )

    assert first.counts.available_nodes == 31
    assert first.counts.included_nodes == 10
    assert first.additional_starting_points == 21
    assert second.additional_starting_points == 11
    assert {node.id for node in first.nodes}.isdisjoint(node.id for node in second.nodes)


def test_call_flow_seeds_are_callable_only_ranked_and_report_truthful_static_counts(tmp_path: Path) -> None:
    result = GraphProjectionService().function_flow(
        call_flow_repository(tmp_path),
        request=GraphProjectionRequest(
            projection_mode="seeds",
            node_types=["function", "method", "external_call", "unresolved_call"],
            edge_types=["calls", "calls_external", "calls_unresolved"],
            seed_limit=12,
        ),
    )

    assert result.seed_strategy == "callable-starting-points/v1"
    assert all(node.type in {"function", "method"} for node in result.nodes)
    assert result.edges == []
    assert result.coverage.measured == {
        "indexed_callables": 4,
        "resolved_call_relations": 4,
        "external_call_relations": 1,
        "unresolved_call_relations": 1,
        "direct_recursive_callables": 1,
    }
    assert result.coverage.state == "limited"
    assert result.coverage.unknown == ["unresolved_call_targets"]
    seed_by_id = {seed.node_id: seed for seed in result.seeds}
    assert "many_callees" in seed_by_id["root"].reason_codes
    assert "direct_recursion" in seed_by_id["recursive"].reason_codes


def test_call_flow_neighbor_projection_preserves_root_relations_and_classified_targets(tmp_path: Path) -> None:
    result = GraphProjectionService().function_flow(
        call_flow_repository(tmp_path),
        request=GraphProjectionRequest(
            projection_mode="neighbors",
            root_keys=["root"],
            node_types=["function", "method", "external_call", "unresolved_call"],
            edge_types=["calls", "calls_external", "calls_unresolved"],
            direction="both",
            max_depth=6,
            max_nodes=5,
            max_edges=12,
        ),
    )

    assert result.projection.max_depth == 1
    assert "call-site" not in {node.id for node in result.nodes}
    assert {node.id for node in result.nodes} == {"caller", "root", "callee", "external", "unresolved"}
    assert {(edge.source, edge.target, edge.type) for edge in result.edges} == {
        ("caller", "root", "calls"),
        ("root", "callee", "calls"),
        ("root", "external", "calls_external"),
        ("root", "unresolved", "calls_unresolved"),
    }
    assert result.expansion is not None
    assert result.expansion.incoming_available == 1
    assert result.expansion.outgoing_available == 3
    assert result.expansion.included_neighbors == 4
    assert result.expansion.remaining_neighbors == 0
    assert all(edge.source in {node.id for node in result.nodes} for edge in result.edges)
    assert all(edge.target in {node.id for node in result.nodes} for edge in result.edges)


def test_value_flow_seeds_are_stable_semantic_candidates_without_broad_edges(tmp_path: Path) -> None:
    repository = value_flow_repository(tmp_path)
    reversed_repository = value_flow_repository(tmp_path)
    reversed_repository.graph_nodes.reverse()
    reversed_repository.graph_edges.reverse()
    request = GraphProjectionRequest(
        projection_mode="seeds",
        root_keys=[value_context(kind="scope", file_path="domain/totals.py", start_line=4, end_line=6)],
        node_types=["dfg_node"],
        seed_limit=3,
    )

    first = GraphProjectionService().data_flow(repository, request=request)
    second = GraphProjectionService().data_flow(reversed_repository, request=request)

    assert first.seed_strategy == "value-context-starting-points/v1"
    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [node.role for node in first.nodes] == ["parameter", "definition", "use"]
    assert first.edges == []
    assert first.counts.available_nodes == 4
    assert first.counts.included_nodes == 3
    assert first.counts.available_edges == 3
    assert first.additional_starting_points == 1
    assert first.coverage.state == "limited"
    assert first.coverage.measured == {
        "indexed_value_nodes": 4,
        "parameter_nodes": 1,
        "definition_nodes": 1,
        "use_nodes": 2,
        "supported_value_relations": 3,
    }
    assert first.coverage.unknown == ["interprocedural_value_flow_unavailable"]
    assert "has_supported_use" in first.seeds[0].reason_codes


def test_value_flow_requires_context_and_resolves_exact_source_token(tmp_path: Path) -> None:
    repository = value_flow_repository(tmp_path)
    service = GraphProjectionService()

    empty = service.data_flow(
        repository,
        request=GraphProjectionRequest(projection_mode="seeds", node_types=["dfg_node"]),
    )
    exact = service.data_flow(
        repository,
        request=GraphProjectionRequest(
            projection_mode="seeds",
            root_keys=[value_context(kind="token", file_path="domain/totals.py", line=5, value="price")],
            node_types=["dfg_node"],
        ),
    )

    assert empty.seed_strategy == "value-context-required/v1"
    assert empty.nodes == []
    assert empty.edges == []
    assert [node.id for node in exact.nodes] == ["parameter-use"]
    assert exact.seeds[0].outgoing_available == 1
    assert exact.counts.available_edges == 2


def test_value_flow_neighbor_projection_is_one_hop_and_respects_value_direction(tmp_path: Path) -> None:
    service = GraphProjectionService()
    repository = value_flow_repository(tmp_path)
    both = service.data_flow(
        repository,
        request=GraphProjectionRequest(
            projection_mode="neighbors",
            root_keys=["definition"],
            node_types=["dfg_node"],
            direction="both",
            max_depth=6,
            max_nodes=8,
            max_edges=12,
        ),
    )

    assert both.projection.max_depth == 1
    assert {node.id for node in both.nodes} == {"definition", "parameter-use", "return-use"}
    assert {(edge.source, edge.target, edge.type) for edge in both.edges} == {
        ("parameter-use", "definition", "dfg_computed_from"),
        ("definition", "return-use", "dfg_returned"),
    }
    assert both.expansion is not None
    assert both.expansion.incoming_available == 1
    assert both.expansion.outgoing_available == 1
    assert both.expansion.included_neighbors == 2

    incoming = service.data_flow(
        repository,
        request=GraphProjectionRequest(
            projection_mode="neighbors",
            root_keys=["definition"],
            node_types=["dfg_node"],
            direction="incoming",
            max_nodes=8,
        ),
    )
    assert {node.id for node in incoming.nodes} == {"definition", "parameter-use"}
    assert [(edge.source, edge.target) for edge in incoming.edges] == [("parameter-use", "definition")]


def test_value_flow_exposes_bounded_resolved_call_boundary_without_global_fallback(tmp_path: Path) -> None:
    repository = value_flow_repository(tmp_path)
    repository.graph_nodes.append(
        GraphNodeDTO(
            id="caller-argument",
            type="dfg_node",
            role="argument",
            label="argument: price",
            file_path="api/orders.py",
            start_line=12,
        )
    )
    repository.graph_edges.append(
        GraphEdgeDTO(
            source="caller-argument",
            target="parameter",
            type="dfg_argument_to_parameter",
            confidence=0.9,
            evidence_level="inferred",
        )
    )
    service = GraphProjectionService()

    seeds = service.data_flow(
        repository,
        request=GraphProjectionRequest(
            projection_mode="seeds",
            root_keys=[value_context(kind="token", file_path="api/orders.py", line=12, value="price")],
            node_types=["dfg_node"],
        ),
    )
    expanded = service.data_flow(
        repository,
        request=GraphProjectionRequest(
            projection_mode="neighbors",
            root_keys=["caller-argument"],
            node_types=["dfg_node"],
            direction="outgoing",
            max_depth=6,
        ),
    )

    assert [node.id for node in seeds.nodes] == ["caller-argument"]
    assert seeds.edges == []
    assert seeds.coverage.unknown == ["interprocedural_value_flow_limited"]
    assert {node.id for node in expanded.nodes} == {"caller-argument", "parameter"}
    assert [(edge.source, edge.target, edge.type) for edge in expanded.edges] == [
        ("caller-argument", "parameter", "dfg_argument_to_parameter")
    ]
    assert expanded.projection.max_depth == 1


def chain_repository(tmp_path: Path, node_count: int) -> RepositoryState:
    return RepositoryState(
        id="repo-graph",
        name="Graph fixture",
        source_type="upload_folder",
        source_uri=None,
        source_path=tmp_path,
        status="indexed",
        current_index_version=7,
        graph_nodes=[
            GraphNodeDTO(id=f"node-{index}", type="function", label=f"Node {index}", file_path=f"src/{index}.py")
            for index in range(node_count)
        ],
        graph_edges=[
            GraphEdgeDTO(source=f"node-{index}", target=f"node-{index + 1}", type="calls", confidence=0.9)
            for index in range(node_count - 1)
        ],
    )


def dependency_repository(
    tmp_path: Path,
    *,
    paths: list[str],
    relations: list[tuple[int, int]],
    relation_type: str = "imports_internal",
    node_types: list[str] | None = None,
) -> RepositoryState:
    types = node_types or ["file"] * len(paths)
    return RepositoryState(
        id="repo-dependencies",
        name="Dependency fixture",
        source_type="upload_folder",
        source_uri=None,
        source_path=tmp_path,
        status="indexed",
        current_index_version=7,
        graph_nodes=[
            GraphNodeDTO(
                id=f"node-{index}",
                type=types[index],
                label=Path(path).name,
                file_path=path if types[index] == "file" else None,
            )
            for index, path in enumerate(paths)
        ],
        graph_edges=[
            GraphEdgeDTO(
                source=f"node-{source}",
                target=f"node-{target}",
                type=relation_type,
                confidence=0.9,
            )
            for source, target in relations
        ],
    )


def request_flow_repository(tmp_path: Path) -> RepositoryState:
    return RepositoryState(
        id="repo-request-flow",
        name="Request flow fixture",
        source_type="upload_folder",
        source_uri=None,
        source_path=tmp_path,
        status="indexed",
        current_index_version=7,
        graph_nodes=[
            GraphNodeDTO(id="endpoint", type="endpoint", label="GET /notes", file_path="api/routes.py"),
            GraphNodeDTO(id="client-call", type="api_call", label="loadNotes", file_path="web/api.ts"),
            GraphNodeDTO(id="unmatched-client", type="api_call", label="loadDrafts", file_path="web/api.ts"),
            GraphNodeDTO(id="handler", type="function", label="list_notes", file_path="api/routes.py"),
            GraphNodeDTO(id="service", type="function", label="fetch_notes", file_path="services/notes.py"),
            GraphNodeDTO(id="call-site", type="call_site", label="fetch_notes()", file_path="api/routes.py"),
        ],
        graph_edges=[
            GraphEdgeDTO(source="client-call", target="endpoint", type="calls_api", confidence=0.95),
            GraphEdgeDTO(source="endpoint", target="handler", type="exposes_endpoint", confidence=1),
            GraphEdgeDTO(source="handler", target="service", type="calls", confidence=0.9),
            GraphEdgeDTO(source="handler", target="call-site", type="contains_call", confidence=1),
        ],
    )


def call_flow_repository(tmp_path: Path) -> RepositoryState:
    return RepositoryState(
        id="repo-call-flow",
        name="Call flow fixture",
        source_type="upload_folder",
        source_uri=None,
        source_path=tmp_path,
        status="indexed",
        current_index_version=9,
        graph_nodes=[
            GraphNodeDTO(id="caller", type="function", label="endpoint_handler", file_path="api/routes.py", start_line=12),
            GraphNodeDTO(id="root", type="method", label="ReservationService.create", file_path="services/reservation.py", start_line=40, end_line=72),
            GraphNodeDTO(id="callee", type="function", label="validate", file_path="services/validation.py", start_line=8),
            GraphNodeDTO(id="recursive", type="function", label="walk_tree", file_path="core/tree.py", start_line=21),
            GraphNodeDTO(id="external", type="external_call", label="vendor.send", file_path="services/reservation.py", start_line=61),
            GraphNodeDTO(id="unresolved", type="unresolved_call", label="plugin.execute", file_path="services/reservation.py", start_line=66),
            GraphNodeDTO(id="call-site", type="call_site", label="validate()", file_path="services/reservation.py", start_line=45),
        ],
        graph_edges=[
            GraphEdgeDTO(source="caller", target="root", type="calls", confidence=0.96),
            GraphEdgeDTO(source="root", target="callee", type="calls", confidence=0.94, metadata={"path": "services/reservation.py", "line": "45"}),
            GraphEdgeDTO(source="root", target="external", type="calls_external", confidence=0.68),
            GraphEdgeDTO(source="root", target="unresolved", type="calls_unresolved", confidence=0.25),
            GraphEdgeDTO(source="recursive", target="recursive", type="calls", confidence=0.91),
            GraphEdgeDTO(source="callee", target="recursive", type="calls", confidence=0.9),
            GraphEdgeDTO(source="root", target="call-site", type="contains_call", confidence=0.8),
        ],
    )


def value_flow_repository(tmp_path: Path) -> RepositoryState:
    return RepositoryState(
        id="repo-value-flow",
        name="Value flow fixture",
        source_type="upload_folder",
        source_uri=None,
        source_path=tmp_path,
        status="indexed",
        current_index_version=11,
        graph_nodes=[
            GraphNodeDTO(id="parameter", type="dfg_node", role="parameter", label="parameter: price", file_path="domain/totals.py", start_line=4),
            GraphNodeDTO(id="parameter-use", type="dfg_node", role="use", label="use: price", file_path="domain/totals.py", start_line=5),
            GraphNodeDTO(id="definition", type="dfg_node", role="definition", label="definition: subtotal", file_path="domain/totals.py", start_line=5),
            GraphNodeDTO(id="return-use", type="dfg_node", role="use", label="use: subtotal", file_path="domain/totals.py", start_line=6),
            GraphNodeDTO(id="isolated-use", type="dfg_node", role="use", label="use: tax", file_path="domain/totals.py", start_line=8),
        ],
        graph_edges=[
            GraphEdgeDTO(source="parameter", target="parameter-use", type="dfg_reaches", confidence=0.85, evidence_level="inferred"),
            GraphEdgeDTO(source="parameter-use", target="definition", type="dfg_computed_from", confidence=0.85, evidence_level="inferred"),
            GraphEdgeDTO(source="definition", target="return-use", type="dfg_returned", confidence=0.85, evidence_level="inferred"),
        ],
    )


def value_context(**payload: object) -> str:
    compact = {
        "k": payload["kind"],
        "f": payload["file_path"],
    }
    if payload["kind"] == "token":
        compact.update({"l": payload["line"], "v": payload["value"]})
    else:
        compact.update({"s": payload["start_line"], "e": payload["end_line"]})
    return f"value-context:v1:{quote(json.dumps(compact, separators=(',', ':')))}"
