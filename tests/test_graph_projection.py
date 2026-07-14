from __future__ import annotations

from pathlib import Path

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
