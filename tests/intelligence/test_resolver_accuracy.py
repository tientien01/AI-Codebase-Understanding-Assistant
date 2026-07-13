from __future__ import annotations

import hashlib

from app.services.code_analysis.adapters.python_adapter import PythonAdapter
from app.services.code_analysis.models import ParseRequest
from app.services.code_analysis.resolver import PythonReferenceResolver


SOURCE = (
    "import json as js\n"
    "from .user import User as Account\n\n"
    "def helper(value):\n"
    "    return value\n\n"
    "class First:\n"
    "    def load(self):\n"
    "        return 1\n\n"
    "    def run(self):\n"
    "        return self.load()\n\n"
    "class Second:\n"
    "    def load(self):\n"
    "        return 2\n\n"
    "def execute(value):\n"
    "    helper(value)\n"
    "    len(value)\n"
    "    js.loads(value)\n"
    "    First.load()\n"
    "    load()\n"
    "    missing()\n"
)


def artifact(file_paths: tuple[str, ...] = ("app/service.py", "app/user.py")):
    request = ParseRequest(
        repository_id="repo_resolution",
        index_version_id="idx_resolution_v1",
        file_path="app/service.py",
        language="python",
        content_hash=hashlib.sha256(SOURCE.encode("utf-8")).hexdigest(),
        source=SOURCE,
    )
    module = PythonAdapter().parse(request)
    return PythonReferenceResolver().resolve(module, file_paths)


def by_raw_reference():
    grouped: dict[str, list] = {}
    for reference in artifact().references:
        grouped.setdefault(reference.raw_reference, []).append(reference)
    return grouped


def test_resolution_matrix_retains_every_import_and_call() -> None:
    grouped = by_raw_reference()

    assert len(artifact().references) == 9
    assert grouped["json"][0].unresolved_reason == "stdlib_module"
    assert grouped["user.User"][0].outcome == "resolved"
    assert grouped["user.User"][0].target_keys == ("file:v1:app/user.py",)
    assert grouped["helper"][0].outcome == "resolved"
    assert grouped["self.load"][0].outcome == "resolved"
    assert grouped["First.load"][0].outcome == "resolved"
    assert grouped["load"][0].outcome == "ambiguous"
    assert len(grouped["load"][0].target_keys) == 2
    assert grouped["len"][0].unresolved_reason == "builtin_target"
    assert grouped["js.loads"][0].unresolved_reason == "stdlib_target"
    assert grouped["missing"][0].unresolved_reason == "target_not_found"


def test_outcome_shapes_and_provenance_are_strict() -> None:
    for reference in artifact().references:
        assert reference.schema_version == "resolved-reference/v1"
        assert reference.canonical_key.startswith("reference:v1:")
        assert reference.repository_id == "repo_resolution"
        assert reference.index_version_id == "idx_resolution_v1"
        assert reference.source_file_key == "file:v1:app/service.py"
        assert reference.source_spans[0].content_hash.startswith("sha256:")
        assert reference.source_spans[0].start_line >= 1
        if reference.outcome == "resolved":
            assert len(reference.target_keys) == 1
            assert reference.support_type == "static_resolved"
            assert reference.unresolved_reason is None
        elif reference.outcome == "ambiguous":
            assert len(reference.target_keys) >= 2
            assert reference.support_type == "static_ambiguous"
            assert reference.unresolved_reason is None
        else:
            assert not reference.target_keys
            assert reference.support_type == "source_exact"
            assert reference.unresolved_reason


def test_resolution_is_deterministic_under_catalog_input_order() -> None:
    first = artifact(("app/service.py", "app/user.py", "README.md")).to_json()
    second = artifact(("README.md", "app/user.py", "app/service.py")).to_json()

    assert first == second


def test_duplicate_internal_module_candidates_are_ambiguous() -> None:
    result = artifact(("packages/one/app/user.py", "packages/two/app/user.py"))
    reference = next(item for item in result.references if item.raw_reference == "user.User")

    assert reference.outcome == "ambiguous"
    assert reference.target_keys == (
        "file:v1:packages/one/app/user.py",
        "file:v1:packages/two/app/user.py",
    )


def test_dynamic_attribute_call_stays_unresolved() -> None:
    source = "def run(service):\n    return service.load()\n"
    request = ParseRequest(
        repository_id="repo_dynamic",
        index_version_id="idx_dynamic_v1",
        file_path="app/dynamic.py",
        language="python",
        content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        source=source,
    )
    module = PythonAdapter().parse(request)
    reference = PythonReferenceResolver().resolve(module, ("app/dynamic.py",)).references[0]

    assert reference.raw_reference == "service.load"
    assert reference.outcome == "unresolved"
    assert reference.unresolved_reason == "dynamic_attribute_target"
