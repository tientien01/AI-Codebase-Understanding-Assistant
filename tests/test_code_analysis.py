from __future__ import annotations

from pathlib import Path

from app.services.chunking_service import ChunkingService
from app.services.index_models import FileRecord, RepositoryState
from app.services.parsing.parser_service import ParserService


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
