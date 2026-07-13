from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_graph_use_cases
from app.core.auth import require_api_auth
from app.schemas.graph import (
    GraphExpansionRequest,
    GraphExpansionResponse,
    GraphResponse,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
)
from app.services.application.use_cases import GraphUseCases


router = APIRouter(prefix="/repositories", tags=["repositories"], dependencies=[Depends(require_api_auth)])


@router.get("/{repository_id}/graph", response_model=GraphResponse)
def get_graph(
    repository_id: str,
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return service.get_graph(repository_id)


@router.get("/{repository_id}/graph/project-map", response_model=GraphResponse)
def get_project_map_graph(
    repository_id: str,
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return service.get_project_map_graph(repository_id)


@router.get("/{repository_id}/graph/dependencies", response_model=GraphResponse)
def get_dependency_graph(
    repository_id: str,
    file_path: str | None = None,
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return service.get_dependency_graph(repository_id, file_path)


@router.get("/{repository_id}/graph/api-flow", response_model=GraphResponse)
def get_api_flow_graph(
    repository_id: str,
    endpoint_id: str | None = None,
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return service.get_api_flow_graph(repository_id, endpoint_id)


@router.get("/{repository_id}/graph/function-flow", response_model=GraphResponse)
def get_function_flow_graph(
    repository_id: str,
    symbol_id: str | None = None,
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return service.get_function_flow_graph(repository_id, symbol_id)


@router.get("/{repository_id}/graph/data-flow", response_model=GraphResponse)
def get_data_flow_graph(
    repository_id: str,
    symbol_id: str | None = None,
    service: GraphUseCases = Depends(get_graph_use_cases),
) -> GraphResponse:
    return service.get_data_flow_graph(repository_id, symbol_id)


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
