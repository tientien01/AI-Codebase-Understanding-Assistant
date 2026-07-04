from __future__ import annotations

from pathlib import Path

from app.schemas.api import GraphNodeDTO
from app.services.chunking_service import ChunkingService
from app.services.graph_service import GraphService
from app.services.index_models import EndpointRecord, FileRecord, RepositoryState, SymbolRecord
from app.services.parser_service import ParserService
from app.services.retrieval_service import RetrievalService
from app.services.scanner_service import ScannerService
from app.services.text_utils import node_id


def test_scanner_skips_secret_and_dependency_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    dependency_dir = tmp_path / "node_modules"
    dependency_dir.mkdir()
    (dependency_dir / "package.js").write_text("console.log('skip')\n", encoding="utf-8")
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
    assert any(endpoint.path == "/login" and endpoint.method == "POST" for endpoint in repository.endpoints)
    assert any(chunk.chunk_type == "endpoint" for chunk in repository.chunks)
    assert any(edge.type == "imports" and edge.target == node_id("module", "fastapi") for edge in repository.graph_edges)
    assert any(edge.type == "calls" and edge.target == node_id("symbol", "routes.py:helper") for edge in repository.graph_edges)


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
        ],
        endpoints=[
            EndpointRecord("POST", "/login", "login", "backend/routes.py", 1, 2),
        ],
        graph_nodes=[
            GraphNodeDTO(id="api_call_login", type="api_call", label="POST /api/login", file_path="frontend/authApi.ts"),
        ],
    )

    GraphService().build_graph(repository)

    assert any(edge.type == "exposes_endpoint" for edge in repository.graph_edges)
    assert any(edge.type == "calls_api" and edge.source == "api_call_login" for edge in repository.graph_edges)


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
