from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.services.chunking_service import ChunkingService
from app.services.code_analysis.adapters.python_adapter import PythonAdapter
from app.services.code_analysis.models import ParseRequest
from app.services.index_models import FileRecord, RepositoryState
from app.services.parsing.canonical_python_parser import CanonicalPythonParser
from app.services.parsing.parser_service import ParserService


SOURCE = (
    "import json as json_lib\n"
    "from app.auth import User as AuthUser\n\n"
    "class Service:\n"
    "    async def load(self, user_id):\n"
    "        return json_lib.loads(user_id)\n"
)


def parse_request(source: str = SOURCE) -> ParseRequest:
    return ParseRequest(
        repository_id="repo_golden",
        index_version_id="idx_golden_v1",
        file_path="app/service.py",
        language="python",
        content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        source=source,
    )


def semantic_golden(module) -> dict[str, object]:
    service = module.classes[0]
    load = service.body[0]
    return {
        "schema_version": module.schema_version,
        "repository_id": module.repository_id,
        "index_version_id": module.index_version_id,
        "file_key": module.file_key,
        "content_hash": module.content_hash,
        "adapter": [module.adapter_name, module.adapter_version],
        "language": module.language,
        "imports": [
            [item.module, item.imported_name, item.alias, item.start_line, item.end_line]
            for item in module.imports
        ],
        "symbols": [
            [service.kind, service.qualified_name, service.start_line, service.end_line],
            [load.kind, load.qualified_name, load.start_line, load.end_line],
        ],
        "parameters": [item.name for item in load.parameters],
        "diagnostics": module.diagnostics,
    }


def test_python_adapter_matches_reviewed_golden_envelope() -> None:
    module = PythonAdapter().parse(parse_request())

    assert semantic_golden(module) == {
        "schema_version": "parsed-file/v1",
        "repository_id": "repo_golden",
        "index_version_id": "idx_golden_v1",
        "file_key": "file:v1:app/service.py",
        "content_hash": f"sha256:{hashlib.sha256(SOURCE.encode('utf-8')).hexdigest()}",
        "adapter": ["python-ast", "python-ast-ir-v1"],
        "language": "python",
        "imports": [
            ["json", None, "json_lib", 1, 1],
            ["app.auth", "User", "AuthUser", 2, 2],
        ],
        "symbols": [
            ["class", "Service", 4, 6],
            ["function", "Service.load", 5, 6],
        ],
        "parameters": ["self", "user_id"],
        "diagnostics": [],
    }


def test_python_adapter_serialization_is_deterministic_and_json_safe() -> None:
    first = PythonAdapter().parse(parse_request()).to_json()
    second = PythonAdapter().parse(parse_request()).to_json()

    assert first == second
    payload = json.loads(first)
    assert payload["file_key"] == "file:v1:app/service.py"
    assert SOURCE not in first


def test_line_shift_preserves_semantic_symbol_identity() -> None:
    base = PythonAdapter().parse(parse_request("def load(value):\n    return value\n"))
    shifted = PythonAdapter().parse(parse_request("\n\n\ndef load(value):\n    return value\n"))

    assert base.functions[0].id == shifted.functions[0].id
    assert base.functions[0].qualified_name == shifted.functions[0].qualified_name
    assert base.functions[0].start_line != shifted.functions[0].start_line


def test_malformed_python_returns_only_a_typed_diagnostic() -> None:
    module = PythonAdapter().parse(parse_request("def broken(:\n    pass\n"))

    assert not module.imports
    assert not module.classes
    assert not module.functions
    assert len(module.diagnostics) == 1
    assert module.diagnostics[0] == {
        "file_path": "app/service.py",
        "language": "python",
        "parser": "python-ast-ir-v1",
        "stage": "parse",
        "severity": "error",
        "message": "Python syntax error. File could not be converted to IR.",
        "line": 1,
    }


@pytest.mark.parametrize(
    "file_path",
    ["/host/app.py", "C:/host/app.py", "../app.py", "app\\service.py", "app//service.py"],
)
def test_parse_request_rejects_noncanonical_or_host_paths(file_path: str) -> None:
    with pytest.raises(ValueError, match="canonical relative POSIX path"):
        ParseRequest(
            repository_id="repo_golden",
            index_version_id="idx_golden_v1",
            file_path=file_path,
            language="python",
            content_hash="0" * 64,
            source="pass\n",
        )


def test_parser_service_invokes_the_canonical_python_adapter_once(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "service.py"
    source_path.write_text("def load(value):\n    return value\n", encoding="utf-8")
    repository = RepositoryState(
        id="repo_boundary",
        name="boundary",
        source_type="upload_folder",
        source_uri=None,
        source_path=tmp_path,
        files=[
            FileRecord(
                path="service.py",
                absolute_path=source_path,
                language="python",
                file_type="source",
                size_bytes=source_path.stat().st_size,
                content_hash="legacy-placeholder",
            )
        ],
    )
    calls = 0
    original_parse = PythonAdapter.parse

    def counted_parse(self, request):
        nonlocal calls
        calls += 1
        return original_parse(self, request)

    monkeypatch.setattr(PythonAdapter, "parse", counted_parse)

    parser = ParserService(ChunkingService())
    assert isinstance(parser.parsers["python"], CanonicalPythonParser)
    parser.parse_files(repository)

    assert calls == 1
    assert [symbol.name for symbol in repository.symbols] == ["load"]


def test_malformed_python_keeps_safe_compatibility_summary(tmp_path: Path) -> None:
    source_path = tmp_path / "broken.py"
    source = "def broken(:\n    pass\n"
    source_path.write_text(source, encoding="utf-8")
    file_record = FileRecord("broken.py", source_path, "python", "source", len(source), "legacy")
    repository = RepositoryState("repo_failure", "failure", "upload_folder", None, tmp_path, files=[file_record])

    ParserService(ChunkingService()).parse_files(repository)

    assert repository.failed_files == 1
    assert file_record.parse_status == "failed"
    assert len(repository.parse_diagnostics) == 1
    assert [chunk.chunk_type for chunk in repository.chunks] == ["file_summary"]


def test_javascript_parser_extracts_configured_imported_and_template_client_calls(tmp_path: Path) -> None:
    sources = {
        "frontend/src/services/apiClient.js": (
            'import axios from "axios";\n'
            'const apiClient = axios.create({ baseURL: "http://localhost:8000/api" });\n'
            "export default apiClient;\n"
        ),
        "frontend/src/services/restaurantService.js": (
            'import apiClient from "./apiClient";\n'
            'export const search = () => apiClient.get("/restaurants/search");\n'
            "export const detail = (restaurantId) => apiClient.get(`/restaurants/${restaurantId}`);\n"
            "export const unresolved = (route) => apiClient.get(route);\n"
        ),
        "frontend/src/services/direct.js": (
            'import axios from "axios";\n'
            'const localClient = axios.create({ baseURL: "/api" });\n'
            'localClient.get("/health");\n'
            'axios.delete("/api/session");\n'
            'fetch("/api/login", { method: "POST" });\n'
        ),
    }
    files: list[FileRecord] = []
    for relative_path, source in sources.items():
        absolute_path = tmp_path / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_text(source, encoding="utf-8")
        files.append(FileRecord(relative_path, absolute_path, "javascript", "source", len(source), "hash"))
    repository = RepositoryState("repo_js_calls", "js calls", "upload_folder", None, tmp_path, files=files)

    ParserService(ChunkingService()).parse_files(repository)

    calls = [node for node in repository.graph_nodes if node.type == "api_call"]
    assert [node.label for node in calls] == [
        "GET /restaurants/search",
        "GET /restaurants/{restaurantId}",
        "GET /api/health",
        "DELETE /api/session",
        "POST /api/login",
    ]
    assert all(node.start_line and node.end_line and node.file_path for node in calls)
    assert not any("unresolved" in node.label.lower() for node in calls)
