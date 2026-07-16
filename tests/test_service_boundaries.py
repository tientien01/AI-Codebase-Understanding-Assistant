from __future__ import annotations

from importlib import import_module
from pathlib import Path

from fastapi.routing import APIRoute

from app.api.dependencies import (
    application_container,
    get_assistant_use_cases,
    get_exploration_use_cases,
    get_graph_use_cases,
    get_import_session_service,
    get_indexing_use_cases,
    get_repository_use_cases,
    get_search_use_cases,
    get_settings_service,
)
from app.schemas.api import GraphNodeDTO
from app.services.chat.llm_client import LLMClient
from app.services.chunking_service import ChunkingService
from app.services.graph.graph_service import GraphService
from app.services.index_models import EndpointRecord, FileRecord, RepositoryState, SymbolRecord
from app.services.parsing.parser_service import ParserService
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.scanning.scanner_service import ScannerService
from app.services.text_utils import node_id


ROUTE_DEPENDENCIES = {
    "app.api.v1.routes.assistant": get_assistant_use_cases,
    "app.api.v1.routes.exploration": get_exploration_use_cases,
    "app.api.v1.routes.graph": get_graph_use_cases,
    "app.api.v1.routes.import_sessions": get_import_session_service,
    "app.api.v1.routes.indexing": get_indexing_use_cases,
    "app.api.v1.routes.repositories": get_repository_use_cases,
    "app.api.v1.routes.search": get_search_use_cases,
    "app.api.v1.routes.settings": get_settings_service,
}


def test_api_routes_use_domain_specific_dependencies() -> None:
    for module_name, expected_dependency in ROUTE_DEPENDENCIES.items():
        module = import_module(module_name)
        for route in module.router.routes:
            if isinstance(route, APIRoute):
                dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
                assert expected_dependency in dependency_calls


def test_api_routes_do_not_import_the_compatibility_facade() -> None:
    for module_name in ROUTE_DEPENDENCIES:
        module = import_module(module_name)
        source = Path(module.__file__).read_text(encoding="utf-8")

        assert "app.services.codebase_service" not in source
        assert "codebase_service" not in source


def test_application_dependencies_share_one_composition_root() -> None:
    assert get_repository_use_cases() is application_container.repository_use_cases
    assert get_import_session_service() is application_container.ingestion
    assert get_indexing_use_cases() is application_container.indexing_use_cases
    assert get_exploration_use_cases() is application_container.exploration_use_cases
    assert get_assistant_use_cases() is application_container.assistant_use_cases
    assert get_graph_use_cases() is application_container.graph_use_cases
    assert get_search_use_cases() is application_container.search_use_cases
    assert get_settings_service() is application_container.settings_service

    repositories = application_container.repositories_service
    assert application_container.repository_use_cases.repositories is repositories
    assert application_container.ingestion.repositories is repositories
    assert application_container.indexing.repositories is repositories
    assert application_container.exploration_use_cases.repositories is repositories
    assert application_container.assistant_use_cases.repositories is repositories
    assert application_container.graph_use_cases.repositories is repositories


def test_scanner_skips_secret_and_dependency_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    dependency_dir = tmp_path / "node_modules"
    dependency_dir.mkdir()
    (dependency_dir / "package.js").write_text("console.log('skip')\n", encoding="utf-8")
    debug_dir = tmp_path / ".ai-codebase"
    debug_dir.mkdir()
    (debug_dir / "parse_output.json").write_text("{}\n", encoding="utf-8")
    repository = RepositoryState(
        id="repo_test",
        name="test",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
    )

    files = ScannerService().scan_files(repository)

    assert [file.path for file in files] == ["app.py"]


def test_parser_extracts_fastapi_endpoint_and_symbol(tmp_path: Path) -> None:
    source = tmp_path / "routes.py"
    source.write_text(
        "from fastapi import APIRouter\n\n"
        "router = APIRouter()\n\n"
        "def helper():\n"
        "    return True\n\n"
        "@router.post('/login')\n"
        "async def login():\n"
        "    helper()\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )
    repository = RepositoryState(
        id="repo_test",
        name="test",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
        files=[
            FileRecord(
                path="routes.py",
                absolute_path=source,
                language="python",
                file_type="source",
                size_bytes=source.stat().st_size,
                content_hash="hash",
            )
        ],
    )

    ParserService(ChunkingService()).parse_files(repository)

    assert any(symbol.name == "login" for symbol in repository.symbols)
    helper_symbol = next(symbol for symbol in repository.symbols if symbol.name == "helper")
    assert any(endpoint.path == "/login" and endpoint.method == "POST" for endpoint in repository.endpoints)
    assert any(chunk.chunk_type == "endpoint" for chunk in repository.chunks)
    assert any(edge.type == "imports" and edge.target == node_id("module", "fastapi") for edge in repository.graph_edges)
    assert any(edge.type == "calls" and edge.target == helper_symbol.id for edge in repository.graph_edges)


def test_parser_creates_chunks_for_new_source_languages(tmp_path: Path) -> None:
    source = tmp_path / "main.go"
    source.write_text("package main\n\nfunc Login() bool {\n    return true\n}\n", encoding="utf-8")
    repository = RepositoryState(
        id="repo_test",
        name="test",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
        files=[
            FileRecord(
                path="main.go",
                absolute_path=source,
                language="go",
                file_type="source",
                size_bytes=source.stat().st_size,
                content_hash="hash",
            )
        ],
    )

    ParserService(ChunkingService()).parse_files(repository)

    assert repository.chunks
    assert repository.chunks[0].file_path == "main.go"
    assert any(symbol.name == "Login" and symbol.symbol_type == "function" for symbol in repository.symbols)


def test_graph_links_frontend_api_call_to_matching_endpoint(tmp_path: Path) -> None:
    repository = RepositoryState(
        id="repo_test",
        name="test",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
        files=[
            FileRecord("backend/routes.py", tmp_path / "backend/routes.py", "python", "source", 1, "hash"),
            FileRecord("frontend/authApi.ts", tmp_path / "frontend/authApi.ts", "typescript", "source", 1, "hash"),
        ],
        symbols=[
            SymbolRecord("symbol_login", "login", "function", "backend/routes.py", 1, 2),
            SymbolRecord("symbol_login_form", "login_form", "function", "backend/routes.py", 3, 4),
        ],
        endpoints=[
            EndpointRecord("POST", "/login", "login", "backend/routes.py", 1, 2),
            EndpointRecord("GET", "/login", "login_form", "backend/routes.py", 3, 4),
        ],
        graph_nodes=[
            GraphNodeDTO(id="api_call_login", type="api_call", label="POST /api/login", file_path="frontend/authApi.ts"),
        ],
    )

    GraphService().build_graph(repository)

    assert any(edge.type == "exposes_endpoint" for edge in repository.graph_edges)
    assert any(edge.type == "exposes_endpoint" and edge.target == "symbol_login" for edge in repository.graph_edges)
    api_edges = [edge for edge in repository.graph_edges if edge.type == "calls_api" and edge.source == "api_call_login"]
    assert len(api_edges) == 1
    assert api_edges[0].target == node_id("endpoint", "POST:/login")
    assert any(node.type == "folder" and node.coverage == "mapped" for node in repository.graph_nodes)
    assert any(node.type == "file" and node.coverage == "deep_indexed" for node in repository.graph_nodes)


def test_graph_matches_route_templates_by_method_without_guessing_ambiguous_targets(tmp_path: Path) -> None:
    repository = RepositoryState(
        id="repo_templates",
        name="templates",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
        endpoints=[
            EndpointRecord("GET", "/restaurants/{restaurant_id}", "get_restaurant", "backend/restaurants.py", 1, 2),
            EndpointRecord("POST", "/restaurants/{restaurant_id}", "update_restaurant", "backend/restaurants.py", 3, 4),
        ],
        graph_nodes=[
            GraphNodeDTO(
                id="api_call_restaurant",
                type="api_call",
                label="GET /api/restaurants/{restaurantId}",
                file_path="frontend/restaurantService.js",
            ),
        ],
    )

    GraphService().build_graph(repository)

    api_edges = [edge for edge in repository.graph_edges if edge.type == "calls_api"]
    assert len(api_edges) == 1
    assert api_edges[0].target == node_id("endpoint", "GET:/restaurants/{restaurant_id}")


def test_retrieval_classifies_and_scores_login_queries(tmp_path: Path) -> None:
    repository = RepositoryState(
        id="repo_test",
        name="test",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
    )
    ChunkingService().add_chunk(repository, "backend/auth.py", "function", "def authenticate_user(): pass", 1, 1, "authenticate_user")

    retrieval = RetrievalService()
    results = retrieval.search_chunks(repository, "backend/auth.py authenticate_user login flow", limit=3)

    assert retrieval.classify_question("login flow hoat dong nhu the nao?") == "flow_tracing"
    assert results
    assert results[0].file_path == "backend/auth.py"
    assert results[0].symbol_name == "authenticate_user"


def test_llm_client_is_not_configured_for_fake_provider() -> None:
    client = LLMClient(provider="fake", model="fake-chat-model", api_key="")

    assert not client.is_configured
    assert client.generate_grounded_answer("question", "code_question", None) is None
