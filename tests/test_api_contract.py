from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.core.auth import require_api_auth
from app.main import app
from app.schemas import api as compatibility_api


OPENAPI_ARTIFACT = Path(__file__).parents[1] / "docs" / "06-api-and-integrations" / "artifacts" / "openapi-v1.json"
EXPECTED_SCHEMA_EXPORTS = {
    "AccessOperationResponse",
    "ApiTokenCreateRequest",
    "ApiTokenIssuedResponse",
    "BootstrapRequest",
    "ChatRequest",
    "ChatResponse",
    "CitationDTO",
    "EndpointDTO",
    "EndpointListResponse",
    "EvidenceDTO",
    "EvidenceValidationItemDTO",
    "EvidenceValidationRequest",
    "EvidenceValidationResponse",
    "FailedFileDTO",
    "FailedFilesResponse",
    "FileContentResponse",
    "FileTreeNodeDTO",
    "GitHubImportRequest",
    "GraphEdgeDTO",
    "GraphExpansionRequest",
    "GraphExpansionResponse",
    "GraphNodeDTO",
    "GraphResponse",
    "IgnorePatternsResponse",
    "ImpactAnalysisRequest",
    "ImpactAnalysisResponse",
    "ImpactItemDTO",
    "ImpactTargetDTO",
    "ImportantFileDTO",
    "ImportActivityLogDTO",
    "ImportCancelResponse",
    "ImportConfirmRequest",
    "ImportConfirmResponse",
    "ImportDuplicateCandidateDTO",
    "ImportFileStatisticsDTO",
    "ImportIgnoreSummaryDTO",
    "ImportPreviewResponse",
    "ImportProjectSummaryDTO",
    "ImportSecurityWarningDTO",
    "ImportSessionCreateResponse",
    "ImportSessionStatusResponse",
    "IndexJobControlResponse",
    "IndexJobListResponse",
    "IndexJobSummaryDTO",
    "IndexRequest",
    "IndexResponse",
    "IndexStatusResponse",
    "IndexWarningDTO",
    "IndexWarningsResponse",
    "LoginRequest",
    "ModuleDTO",
    "OverviewResponse",
    "ReadingPathItemDTO",
    "ReadingPathResponse",
    "ReadingPathSignalDTO",
    "RepositoryBulkDeleteRequest",
    "RepositoryBulkDeleteResponse",
    "RepositoryCreateResponse",
    "RepositoryDTO",
    "RepositoryDeleteResponse",
    "SearchAskWithEvidenceRequest",
    "SearchResponse",
    "SearchResultDTO",
    "SessionIssuedResponse",
    "SessionResponse",
    "SettingsResponse",
    "SkippedFileDTO",
    "SkippedFilesResponse",
    "StalenessResponse",
    "SymbolDTO",
    "SymbolListResponse",
}
EXPECTED_ROUTE_MODULE_COUNTS = {
    "app.api.v1.routes.auth": 6,
    "app.api.v1.routes.assistant": 4,
    "app.api.v1.routes.exploration": 4,
    "app.api.v1.routes.graph": 8,
    "app.api.v1.routes.import_sessions": 10,
    "app.api.v1.routes.indexing": 10,
    "app.api.v1.routes.repositories": 5,
    "app.api.v1.routes.search": 3,
    "app.api.v1.routes.settings": 2,
}
EXPECTED_SCHEMA_MODULES = {
    "app.schemas.assistant",
    "app.schemas.auth",
    "app.schemas.exploration",
    "app.schemas.graph",
    "app.schemas.imports",
    "app.schemas.indexing",
    "app.schemas.repositories",
    "app.schemas.search",
    "app.schemas.settings",
}


def test_generated_openapi_matches_committed_artifact() -> None:
    committed = json.loads(OPENAPI_ARTIFACT.read_text(encoding="utf-8"))

    assert app.openapi() == committed


def test_route_inventory_and_auth_dependencies_are_preserved() -> None:
    registered_routes: list[tuple[str, APIRoute]] = []
    for registered in app.routes:
        if isinstance(registered, APIRoute):
            registered_routes.append(("", registered))
            continue
        # FastAPI 0.115+ keeps included routers as lightweight registrations.
        # Inspect their original APIRoutes so router-level auth remains testable.
        original_router = getattr(registered, "original_router", None)
        include_context = getattr(registered, "include_context", None)
        if original_router is not None and include_context is not None:
            registered_routes.extend(
                (include_context.prefix, route)
                for route in original_router.routes
                if isinstance(route, APIRoute)
            )

    versioned_routes = [
        route
        for prefix, route in registered_routes
        if f"{prefix}{route.path}".startswith("/api/v1")
    ]

    assert len(registered_routes) == 53
    assert len(versioned_routes) == 52
    assert {
        f"{prefix}{route.path}"
        for prefix, route in registered_routes
        if not f"{prefix}{route.path}".startswith("/api/v1")
    } == {"/health"}
    public_auth_paths = {"/api/v1/auth/bootstrap", "/api/v1/auth/login"}
    for prefix, route in registered_routes:
        full_path = f"{prefix}{route.path}"
        if not full_path.startswith("/api/v1") or full_path in public_auth_paths:
            continue
        assert any(dependency.call is require_api_auth for dependency in route.dependant.dependencies)


def test_openapi_operation_ids_are_present_and_unique() -> None:
    document = app.openapi()
    operation_ids = [
        operation["operationId"]
        for path_item in document["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]

    assert len(operation_ids) == 53
    assert len(operation_ids) == len(set(operation_ids))


def test_graph_projection_openapi_declares_bounded_inputs_and_disclosure_fields() -> None:
    document = app.openapi()
    operation = document["paths"]["/api/v1/repositories/{repository_id}/graph/project-map"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    assert parameters["max_nodes"]["schema"]["maximum"] == 220
    assert parameters["max_edges"]["schema"]["maximum"] == 520
    assert parameters["max_depth"]["schema"]["maximum"] == 6
    assert {"root_keys", "node_types", "edge_types", "direction", "min_confidence", "support_levels"} <= parameters.keys()
    response_schema = document["components"]["schemas"]["GraphResponse"]["properties"]
    assert {"nodes", "edges", "counts", "coverage", "truncation", "unsupported_hops", "can_expand", "provenance"} <= response_schema.keys()

    dependency_operation = document["paths"]["/api/v1/repositories/{repository_id}/graph/dependencies"]["get"]
    dependency_parameters = {parameter["name"]: parameter for parameter in dependency_operation["parameters"]}
    assert {"projection_mode", "dependency_scope", "seed_limit", "neighbor_offset"} <= dependency_parameters.keys()
    assert dependency_parameters["seed_limit"]["schema"]["default"] == 24
    assert dependency_parameters["seed_limit"]["schema"]["maximum"] == 100
    assert dependency_parameters["neighbor_offset"]["schema"]["maximum"] == 100_000
    assert {
        "dependency_scope_used",
        "seed_strategy",
        "seeds",
        "additional_starting_points",
        "expansion",
    } <= response_schema.keys()


def test_folder_import_openapi_declares_batched_session_flow() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/import-sessions/upload-folder/start" in paths
    assert "/api/v1/import-sessions/{import_session_id}/upload-folder-batch" in paths
    assert "/api/v1/import-sessions/{import_session_id}/upload-folder-complete" in paths
    start_schema = paths["/api/v1/import-sessions/upload-folder/start"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert start_schema["$ref"].endswith("/FolderImportStartRequest")


def test_compatibility_schema_module_exports_all_existing_models() -> None:
    exported_models = {
        name
        for name, value in vars(compatibility_api).items()
        if isinstance(value, type) and issubclass(value, BaseModel) and value is not BaseModel
    }

    assert exported_models == EXPECTED_SCHEMA_EXPORTS
    assert {
        getattr(compatibility_api, name).__module__
        for name in exported_models
    } == EXPECTED_SCHEMA_MODULES


def test_routes_are_owned_by_domain_modules() -> None:
    for module_name, expected_count in EXPECTED_ROUTE_MODULE_COUNTS.items():
        module = import_module(module_name)
        routes = [route for route in module.router.routes if isinstance(route, APIRoute)]

        assert len(routes) == expected_count
        assert {route.endpoint.__module__ for route in routes} == {module_name}
