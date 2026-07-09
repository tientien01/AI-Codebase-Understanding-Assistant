from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.services.chunking_service import ChunkingService
from app.services.index_models import FileRecord, RepositoryState
from app.services.parsing.debug_output_service import ParseDebugOutputService
from app.services.parsing.parser_service import ParserService
from app.services.graph.graph_projection_service import GraphProjectionService
from app.services.graph.graph_service import GraphService


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
    assert any(edge.type.startswith("cfg_") for edge in function_flow.edges)
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
