from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.schemas.api import GraphEdgeDTO
from app.services.chunking_service import ChunkingService
from app.services.index_models import FileRecord, RepositoryState
from app.services.parsing.debug_output_service import ParseDebugOutputService
from app.services.parsing.parser_service import ParserService
from app.services.parsing.javascript_parser import JavaScriptTypeScriptParser
from app.services.enrichment.semantic_enrichment_service import SemanticEnrichmentService
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.graph.graph_projection_service import GraphProjectionService
from app.services.graph.graph_service import GraphService
from app.services.impact.impact_analysis_service import ImpactAnalysisService


def parse_python_source(tmp_path: Path, source_text: str) -> RepositoryState:
    source = tmp_path / "sample.py"
    source.write_text(source_text, encoding="utf-8")
    repository = RepositoryState(
        id="repo_code_analysis",
        name="code-analysis-test",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
        files=[
            FileRecord(
                path="sample.py",
                absolute_path=source,
                language="python",
                file_type="source",
                size_bytes=source.stat().st_size,
                content_hash="hash",
            )
        ],
    )
    ParserService(ChunkingService()).parse_files(repository)
    return repository


def parse_python_files(tmp_path: Path, files: dict[str, str]) -> RepositoryState:
    records: list[FileRecord] = []
    for relative_path, source_text in files.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source_text, encoding="utf-8")
        records.append(
            FileRecord(
                path=relative_path,
                absolute_path=path,
                language="python",
                file_type="source",
                size_bytes=path.stat().st_size,
                content_hash=f"hash-{relative_path}",
            )
        )
    repository = RepositoryState(
        id="repo_multi_file",
        name="multi-file-test",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
        files=records,
    )
    ParserService(ChunkingService()).parse_files(repository)
    ChunkingService().create_file_summary_chunks(repository)
    GraphService().build_graph(repository)
    return repository


def test_python_symbol_id_is_stable_when_lines_shift(tmp_path: Path) -> None:
    first = parse_python_source(
        tmp_path,
        "def login(user):\n"
        "    return user\n",
    )
    second = parse_python_source(
        tmp_path,
        "# comment added above the function\n\n"
        "def login(user):\n"
        "    return user\n",
    )

    first_login = next(symbol for symbol in first.symbols if symbol.name == "login")
    second_login = next(symbol for symbol in second.symbols if symbol.name == "login")

    assert first_login.id == second_login.id
    assert first_login.start_line == 1
    assert second_login.start_line == 3


def test_redefined_python_symbols_receive_unique_repeatable_ids(tmp_path: Path) -> None:
    source = (
        "def resolve(value):\n    return value\n\n"
        "def resolve(value):\n    return value + 1\n"
    )

    first = parse_python_source(tmp_path, source)
    second = parse_python_source(tmp_path, source)
    first_ids = [item.id for item in first.symbols if item.name == "resolve"]
    second_ids = [item.id for item in second.symbols if item.name == "resolve"]

    assert len(first_ids) == 2
    assert len(set(first_ids)) == 2
    assert first_ids == second_ids


def test_redefined_javascript_symbols_receive_unique_repeatable_ids(
    tmp_path: Path,
) -> None:
    source = "const resolve = () => 1\nconst resolve = () => 2\n"

    def parse() -> list[str]:
        repository = RepositoryState(
            id="repo_javascript_duplicates",
            name="javascript-duplicates",
            source_type="upload_folder",
            source_uri=None,
            source_path=tmp_path,
        )
        file_record = FileRecord(
            "sample.ts", tmp_path / "sample.ts", "typescript", "source", len(source), "hash"
        )
        JavaScriptTypeScriptParser(ChunkingService()).parse(
            repository, file_record, source
        )
        return [item.id for item in repository.symbols]

    first_ids = parse()
    assert len(first_ids) == 2
    assert len(set(first_ids)) == 2
    assert first_ids == parse()


def test_python_code_analysis_emits_cfg_for_branch(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "def choose(value):\n"
        "    if value:\n"
        "        return value\n"
        "    else:\n"
        "        return 1\n"
        "    return 0\n",
    )

    edge_types = {edge.type for edge in repository.graph_edges}

    assert "cfg_true" in edge_types
    assert "cfg_false" in edge_types
    assert "cfg_return" in edge_types


def test_python_code_analysis_emits_dfg_for_assignment_and_return(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "def build_token(user):\n"
        "    token = create_token(user.id)\n"
        "    return token\n",
    )

    edge_types = {edge.type for edge in repository.graph_edges}
    dfg_labels = {node.label for node in repository.graph_nodes if node.type == "dfg_node"}

    assert "dfg_computed_from" in edge_types
    assert "dfg_returned" in edge_types
    assert "parameter: user" in dfg_labels
    assert "definition: token" in dfg_labels


def test_python_code_analysis_binds_resolved_call_arguments_and_returns(tmp_path: Path) -> None:
    source = (
        "def normalize(value):\n"
        "    return value\n\n"
        "def build(raw):\n"
        "    result = normalize(raw)\n"
        "    return result\n"
    )
    first = parse_python_source(tmp_path, source)
    GraphService().build_graph(first)
    second = parse_python_source(tmp_path, source)
    GraphService().build_graph(second)

    node_by_id = {node.id: node for node in first.graph_nodes}
    relations = {
        (node_by_id[edge.source].label, node_by_id[edge.target].label, edge.type)
        for edge in first.graph_edges
        if edge.type.startswith("dfg_")
    }

    assert ("argument: raw", "parameter: value", "dfg_argument_to_parameter") in relations
    assert ("return: normalize", "call_result: normalize", "dfg_return_to_call_result") in relations
    assert ("call_result: normalize", "definition: result", "dfg_call_result_to_definition") in relations
    assert ("parameter: raw", "use: raw", "dfg_reaches") in relations
    binding = next(edge for edge in first.graph_edges if edge.type == "dfg_argument_to_parameter")
    assert binding.evidence_level == "inferred"
    assert binding.metadata == {
        "path": "sample.py",
        "line": "5",
        "resolution": "static_resolved",
        "scope": "direct_interprocedural",
    }
    assert {
        (edge.source, edge.target, edge.type)
        for edge in first.graph_edges
        if edge.type.startswith("dfg_")
    } == {
        (edge.source, edge.target, edge.type)
        for edge in second.graph_edges
        if edge.type.startswith("dfg_")
    }


def test_python_code_analysis_does_not_bind_ambiguous_or_unresolved_calls(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "class First:\n"
        "    def convert(self, value):\n"
        "        return value\n\n"
        "class Second:\n"
        "    def convert(self, value):\n"
        "        return value\n\n"
        "def build(raw):\n"
        "    ambiguous = convert(raw)\n"
        "    external = vendor_transform(raw)\n"
        "    return external\n",
    )
    GraphService().build_graph(repository)

    edge_types = {edge.type for edge in repository.graph_edges}
    assert "dfg_argument_to_parameter" not in edge_types
    assert "dfg_return_to_call_result" not in edge_types


def test_graph_projection_exposes_project_function_and_data_views(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "def choose(value):\n"
        "    if value:\n"
        "        token = str(value)\n"
        "        return token\n"
        "    return 'empty'\n",
    )
    GraphService().build_graph(repository)
    projection = GraphProjectionService()

    project_map = projection.project_map(repository)
    function_flow = projection.function_flow(repository)
    data_flow = projection.data_flow(repository)

    assert any(node.type == "function" for node in project_map.nodes)
    assert any(edge.type.startswith("calls") for edge in function_flow.edges)
    assert any(edge.type.startswith("dfg_") for edge in data_flow.edges)


def test_graph_edges_reference_existing_nodes_after_build(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "def helper():\n"
        "    return True\n\n"
        "def login():\n"
        "    return helper()\n",
    )

    GraphService().build_graph(repository)

    node_ids = {node.id for node in repository.graph_nodes}
    dangling_edges = [
        edge
        for edge in repository.graph_edges
        if edge.source not in node_ids or edge.target not in node_ids
    ]
    assert dangling_edges == []


def test_graph_schema_normalizes_nodes_edges_and_metadata(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "def login(user):\n"
        "    return user\n",
    )
    repository.graph_edges.append(
        GraphEdgeDTO(
            source="missing",
            target="also_missing",
            type="custom_edge",
            confidence=2.5,
        )
    )

    GraphService().build_graph(repository)

    login_node = next(node for node in repository.graph_nodes if node.label == "login")
    assert login_node.start_line == 1
    assert login_node.end_line == 2
    assert login_node.summary
    assert "function" in login_node.tags
    assert login_node.layer == "application"
    assert login_node.complexity

    assert all(edge.source != "missing" for edge in repository.graph_edges)
    assert all(0 <= edge.confidence <= 1 for edge in repository.graph_edges)
    assert all(edge.weight is not None for edge in repository.graph_edges)
    assert all(edge.evidence_level in {"map", "deep", "inferred"} for edge in repository.graph_edges)
    assert any("Dropped graph edge with missing endpoint" in item["message"] for item in repository.parse_diagnostics)


def test_hybrid_search_returns_endpoint_symbol_and_file_matches(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "from flask import Blueprint\n\n"
        "auth = Blueprint('auth', __name__)\n\n"
        "@auth.route('/login', methods=['GET', 'POST'])\n"
        "def login():\n"
        "    return 'ok'\n",
    )
    ChunkingService().create_file_summary_chunks(repository)
    GraphService().build_graph(repository)

    matches = RetrievalService().hybrid_search(repository, "GET login sample.py", limit=10)

    assert matches
    assert any(match.result_type == "endpoint" for match in matches)
    assert any(match.result_type in {"function", "method"} and match.title == "login" for match in matches)
    assert any(match.result_type == "file" and match.title == "sample.py" for match in matches)
    assert all(match.retrieval_source in {"chunk", "symbol", "endpoint", "file", "graph", "graph_context", "semantic_vector"} for match in matches)
    assert any("login" in match.matched_terms for match in matches)


def test_hybrid_search_uses_fuzzy_symbol_matching(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "def login_user(account):\n"
        "    return account\n",
    )
    ChunkingService().create_file_summary_chunks(repository)
    GraphService().build_graph(repository)

    matches = RetrievalService().hybrid_search(repository, "logn_user", limit=5)

    assert any(match.title == "login_user" for match in matches)


def test_hybrid_search_uses_local_vector_matches_for_semantic_summary(tmp_path: Path) -> None:
    repository = parse_python_files(
        tmp_path,
        {
            "backend/app/api/auth/routes.py": (
                "from flask import Blueprint\n\n"
                "auth = Blueprint('auth', __name__)\n\n"
                "@auth.route('/login', methods=['POST'])\n"
                "def login():\n"
                "    return 'ok'\n"
            ),
        },
    )
    SemanticEnrichmentService(ChunkingService()).enrich(repository)

    matches = RetrievalService().hybrid_search(repository, "authentication", limit=8)

    assert any(match.retrieval_source == "semantic_vector" for match in matches)
    assert any(match.chunk.chunk_type == "semantic_summary" for match in matches)


def test_impact_analysis_finds_files_endpoints_and_tests(tmp_path: Path) -> None:
    repository = parse_python_files(
        tmp_path,
        {
            "app/auth.py": "def authenticate_user(username):\n    return username == 'admin'\n",
            "app/routes.py": (
                "from flask import Blueprint\n"
                "from app.auth import authenticate_user\n\n"
                "auth = Blueprint('auth', __name__)\n\n"
                "@auth.route('/login', methods=['POST'])\n"
                "def login():\n"
                "    return authenticate_user('admin')\n"
            ),
            "tests/test_auth.py": "from app.auth import authenticate_user\n\n\ndef test_auth():\n    assert authenticate_user('admin')\n",
        },
    )

    result = ImpactAnalysisService().analyze(repository, "file", "app/auth.py", max_depth=3)

    assert result.target
    assert result.target.file_path == "app/auth.py"
    assert result.risk_level in {"medium", "high"}
    assert any(item.file_path == "app/routes.py" for item in result.affected_files)
    assert any(item.file_path == "tests/test_auth.py" for item in result.affected_tests)
    assert any("/login" in item.label for item in result.affected_endpoints)
    assert any("Run or inspect related test file tests/test_auth.py" in item for item in result.suggested_checks)


def test_impact_analysis_reports_unresolved_target(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "def login():\n"
        "    return True\n",
    )
    GraphService().build_graph(repository)

    result = ImpactAnalysisService().analyze(repository, "symbol", "missing_symbol")

    assert result.target is None
    assert result.risk_level == "unknown"
    assert result.missing_relations


def test_semantic_enrichment_adds_node_metadata_and_summary_chunks(tmp_path: Path) -> None:
    repository = parse_python_files(
        tmp_path,
        {
            "backend/app/api/auth/routes.py": (
                "from flask import Blueprint\n\n"
                "auth = Blueprint('auth', __name__)\n\n"
                "@auth.route('/login', methods=['POST'])\n"
                "def login():\n"
                "    return 'ok'\n"
            ),
        },
    )

    SemanticEnrichmentService(ChunkingService()).enrich(repository)

    file_node = next(node for node in repository.graph_nodes if node.type == "file")
    endpoint_node = next(node for node in repository.graph_nodes if node.type == "endpoint")
    semantic_chunk = next(chunk for chunk in repository.chunks if chunk.chunk_type == "semantic_summary")

    assert file_node.layer == "api"
    assert "auth" in file_node.tags
    assert "login" in file_node.summary
    assert endpoint_node.summary.startswith("API endpoint")
    assert "POST /login" in semantic_chunk.content


def test_parse_debug_output_contains_files_nodes_edges_and_diagnostics(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "def helper():\n"
        "    return True\n\n"
        "def login():\n"
        "    return helper()\n",
    )
    GraphService().build_graph(repository)

    artifact_path = ParseDebugOutputService().write(repository)

    assert artifact_path == settings.repository_storage_dir / repository.id / "parse_output.json"
    mirror_path = repository.source_path / ".ai-codebase" / "parse_output.json"
    assert mirror_path.exists()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    mirror_payload = json.loads(mirror_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["schema_version"] == "parse-debug-v1"
    assert mirror_payload["metadata"]["primary_artifact_path"] == str(artifact_path)
    assert payload["files"][0]["path"] == "sample.py"
    assert any(node["kind"] == "Function" and node["label"] == "login" for node in payload["nodes"])
    assert any(node["kind"] == "Call" for node in payload["nodes"])
    assert any(edge["type"] == "calls" and edge["resolved"] for edge in payload["edges"])
    assert "errors" in payload
    assert "warnings" in payload


def test_python_endpoint_detector_handles_flask_decorators(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "from flask import Blueprint, render_template\n\n"
        "auth = Blueprint('auth', __name__)\n\n"
        "@auth.route('/login', methods=['GET', 'POST'])\n"
        "def login():\n"
        "    return render_template('login.html')\n",
    )

    endpoint = next(item for item in repository.endpoints if item.handler == "login")

    assert endpoint.path == "/login"
    assert endpoint.method == "GET"
    assert endpoint.metadata["framework"] == "flask"
    assert not any("render_template" in item.get("message", "") for item in repository.parse_diagnostics)


def test_endpoint_detector_keeps_unknown_framework_generic(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "class Router:\n"
        "    def route(self, path):\n"
        "        return lambda func: func\n\n"
        "router = Router()\n\n"
        "@router.route('/custom')\n"
        "def custom():\n"
        "    return 'ok'\n",
    )

    endpoint = next(item for item in repository.endpoints if item.handler == "custom")

    assert endpoint.path == "/custom"
    assert endpoint.metadata["framework"] == "unknown"


def test_python_call_resolver_classifies_builtins_and_imported_calls(tmp_path: Path) -> None:
    repository = parse_python_source(
        tmp_path,
        "import ast\n"
        "from flask import redirect\n\n"
        "def parse(value):\n"
        "    data = ast.literal_eval(value)\n"
        "    return len(data)\n\n"
        "def go():\n"
        "    return redirect('/login')\n",
    )

    edge_types = {edge.type for edge in repository.graph_edges}

    assert "calls_stdlib" in edge_types
    assert "calls_builtin" in edge_types
    assert "calls_framework" in edge_types
    assert not repository.parse_diagnostics


def test_import_resolver_links_internal_python_modules(tmp_path: Path) -> None:
    package_dir = tmp_path / "app"
    package_dir.mkdir()
    user_file = package_dir / "user.py"
    routes_file = package_dir / "routes.py"
    user_file.write_text("class User:\n    pass\n", encoding="utf-8")
    routes_file.write_text("from app.user import User\n\n\ndef load():\n    return User()\n", encoding="utf-8")
    repository = RepositoryState(
        id="repo_imports",
        name="imports",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
        files=[
            FileRecord("app/user.py", user_file, "python", "source", user_file.stat().st_size, "hash-user"),
            FileRecord("app/routes.py", routes_file, "python", "source", routes_file.stat().st_size, "hash-routes"),
        ],
    )

    ParserService(ChunkingService()).parse_files(repository)
    GraphService().build_graph(repository)

    file_nodes = {node.file_path: node.id for node in repository.graph_nodes if node.type == "file"}
    assert any(
        edge.type == "imports_internal"
        and edge.source == file_nodes["app/routes.py"]
        and edge.target == file_nodes["app/user.py"]
        for edge in repository.graph_edges
    )


def test_cfg_dfg_can_be_disabled_for_lightweight_indexing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_cfg_dfg", False)

    repository = parse_python_source(
        tmp_path,
        "def choose(value):\n"
        "    if value:\n"
        "        return value\n"
        "    return 0\n",
    )

    assert not any(edge.type.startswith("cfg_") for edge in repository.graph_edges)
    assert not any(edge.type.startswith("dfg_") for edge in repository.graph_edges)
