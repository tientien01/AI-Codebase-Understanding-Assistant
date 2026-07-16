from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import StringConstraints

from app.api.dependencies import get_graph_use_cases
from app.core.auth import require_api_auth
from app.schemas.graph import (
    GRAPH_NEIGHBOR_OFFSET_MAX,
    GRAPH_SEED_LIMIT_DEFAULT,
    GRAPH_SEED_LIMIT_MAX,
    GraphExpansionRequest,
    GraphExpansionResponse,
    GraphProjectionRequest,
    GraphResponse,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
)
from app.services.application.use_cases import GraphUseCases
from app.services.graph.graph_projection_service import GraphProjectionVersionMismatch


router = APIRouter(prefix="/repositories", tags=["repositories"], dependencies=[Depends(require_api_auth)])
GraphFilter = Annotated[str, StringConstraints(max_length=200)]


def graph_projection_request(
    index_version: int | None = Query(default=None, ge=1),
    root_keys: list[GraphFilter] = Query(default=[], max_length=20),
    node_types: list[GraphFilter] = Query(default=[], max_length=20),
    edge_types: list[GraphFilter] = Query(default=[], max_length=20),
    direction: Literal["outgoing", "incoming", "both"] = Query(default="both"),
    max_depth: int = Query(default=2, ge=0, le=6),
    max_nodes: int = Query(default=220, ge=1, le=220),
    max_edges: int = Query(default=520, ge=0, le=520),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    support_levels: list[GraphFilter] = Query(default=[], max_length=10),
    projection_mode: Literal["full", "seeds", "neighbors"] = Query(default="full"),
    dependency_scope: Literal["adaptive", "internal", "detected"] = Query(default="detected"),
    seed_limit: int = Query(default=GRAPH_SEED_LIMIT_DEFAULT, ge=1, le=GRAPH_SEED_LIMIT_MAX),
    neighbor_offset: int = Query(default=0, ge=0, le=GRAPH_NEIGHBOR_OFFSET_MAX),
) -> GraphProjectionRequest:
    return GraphProjectionRequest(
        index_version=index_version,
        root_keys=root_keys,
        node_types=node_types,
        edge_types=edge_types,
        direction=direction,
        max_depth=max_depth,
        max_nodes=max_nodes,
        max_edges=max_edges,
        min_confidence=min_confidence,
        support_levels=support_levels,
        projection_mode=projection_mode,
        dependency_scope=dependency_scope,
        seed_limit=seed_limit,
        neighbor_offset=neighbor_offset,
    )


def run_projection(action: Callable[[], GraphResponse]) -> GraphResponse:
    try:
        return action()
    except GraphProjectionVersionMismatch as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "GRAPH_INDEX_VERSION_NOT_ACTIVE", "message": str(error), "retryable": False},
        ) from error


@router.get("/{repository_id}/graph", response_model=GraphResponse)
def get_graph(
    repository_id: str,
    projection: GraphProjectionRequest = Depends(graph_projection_request),
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return run_projection(lambda: service.get_graph(repository_id, projection))


@router.get("/{repository_id}/graph/project-map", response_model=GraphResponse)
def get_project_map_graph(
    repository_id: str,
    projection: GraphProjectionRequest = Depends(graph_projection_request),
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return run_projection(lambda: service.get_project_map_graph(repository_id, projection))


@router.get("/{repository_id}/graph/dependencies", response_model=GraphResponse)
def get_dependency_graph(
    repository_id: str,
    file_path: str | None = None,
    projection: GraphProjectionRequest = Depends(graph_projection_request),
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return run_projection(lambda: service.get_dependency_graph(repository_id, file_path, projection))


@router.get("/{repository_id}/graph/api-flow", response_model=GraphResponse)
def get_api_flow_graph(
    repository_id: str,
    endpoint_id: str | None = None,
    projection: GraphProjectionRequest = Depends(graph_projection_request),
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return run_projection(lambda: service.get_api_flow_graph(repository_id, endpoint_id, projection))


@router.get("/{repository_id}/graph/function-flow", response_model=GraphResponse)
def get_function_flow_graph(
    repository_id: str,
    symbol_id: str | None = None,
    projection: GraphProjectionRequest = Depends(graph_projection_request),
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return run_projection(lambda: service.get_function_flow_graph(repository_id, symbol_id, projection))


@router.get("/{repository_id}/graph/data-flow", response_model=GraphResponse)
def get_data_flow_graph(
    repository_id: str,
    symbol_id: str | None = None,
    projection: GraphProjectionRequest = Depends(graph_projection_request),
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return run_projection(lambda: service.get_data_flow_graph(repository_id, symbol_id, projection))


@router.post("/{repository_id}/graph/expand", response_model=GraphExpansionResponse)
def expand_graph_area(
    repository_id: str,
    request: GraphExpansionRequest,
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphExpansionResponse:
    return service.expand_graph_area(repository_id, request.scope_path)


@router.post("/{repository_id}/impact", response_model=ImpactAnalysisResponse)
def analyze_impact(
    repository_id: str,
    request: ImpactAnalysisRequest,
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> ImpactAnalysisResponse:
    return service.analyze_impact(repository_id, request.target_type, request.target_ref, request.max_depth)
