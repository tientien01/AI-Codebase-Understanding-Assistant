from __future__ import annotations

from pathlib import Path

from app.services.chunking_service import ChunkingService
from app.services.code_analysis.graph_candidates import (
    GraphCandidate,
    GraphCandidateNormalizer,
    GraphNormalizationPolicy,
    canonical_edge_key,
)
from app.services.code_analysis.models import SourceSpan
from app.services.index_models import FileRecord, RepositoryState
from app.services.parsing.parser_service import ParserService


REPOSITORY_ID = "repo_graph"
INDEX_VERSION_ID = "idx_graph_v1"
FILE_KEY = "file:v1:app/service.py"
SOURCE_KEY = "symbol:v1:python:function:file%3Av1%3Aapp%2Fservice.py:run"
TARGET_KEY = "symbol:v1:python:function:file%3Av1%3Aapp%2Fservice.py:helper"
SPAN = (SourceSpan(FILE_KEY, 3, 3, "0" * 64),)


def candidate(**overrides) -> GraphCandidate:
    values = {
        "schema_version": "graph-candidate/v1",
        "candidate_kind": "edge",
        "canonical_key": canonical_edge_key("calls", SOURCE_KEY, TARGET_KEY, "reference:v1:test"),
        "repository_id": REPOSITORY_ID,
        "index_version_id": INDEX_VERSION_ID,
        "node_type": None,
        "label": None,
        "source_key": SOURCE_KEY,
        "target_key": TARGET_KEY,
        "relation_type": "calls",
        "origin": "resolver_exact",
        "producer_name": "fixture",
        "producer_version": "1",
        "support_type": "static_resolved",
        "source_spans": SPAN,
        "evidence_reference_key": "reference:v1:test",
    }
    values.update(overrides)
    return GraphCandidate(**values)


def normalize(*items: GraphCandidate, known: frozenset[str] | None = None, minimum: float = 0.0):
    return GraphCandidateNormalizer().normalize(
        tuple(items),
        repository_id=REPOSITORY_ID,
        index_version_id=INDEX_VERSION_ID,
        known_node_keys=known or frozenset({FILE_KEY, SOURCE_KEY, TARGET_KEY}),
        policy=GraphNormalizationPolicy(minimum_inferred_confidence=minimum),
    )


def test_valid_python_pipeline_produces_zero_critical_candidates(tmp_path: Path) -> None:
    source_path = tmp_path / "service.py"
    source_path.write_text("def helper():\n    return True\n\ndef run():\n    return helper()\n", encoding="utf-8")
    repository = RepositoryState(
        id="repo_pipeline",
        name="pipeline",
        source_type="upload_folder",
        source_uri=None,
        source_path=tmp_path,
        files=[FileRecord("service.py", source_path, "python", "source", source_path.stat().st_size, "legacy")],
    )

    ParserService(ChunkingService()).parse_files(repository)

    assert repository.graph_candidates
    assert not repository.graph_validation_issues
    edge = next(item for item in repository.graph_candidates if item.candidate_kind == "edge")
    assert edge.status == "accepted"
    assert edge.origin == "resolver_exact"
    assert edge.support_type == "static_resolved"
    assert edge.source_spans
    assert any(item.type == "calls" for item in repository.graph_edges)


def test_inverse_direction_and_exact_duplicate_are_audited() -> None:
    inverse = candidate(
        canonical_key="edge:v1:called_by:fixture",
        source_key=TARGET_KEY,
        target_key=SOURCE_KEY,
        relation_type="called_by",
    )
    duplicate = candidate()
    report = normalize(inverse, duplicate, duplicate)

    changed = next(item for item in report.candidates if item.normalization_reason == "inverse_direction")
    assert changed.status == "changed"
    assert (changed.source_key, changed.target_key, changed.relation_type) == (SOURCE_KEY, TARGET_KEY, "calls")
    assert any(item.normalization_reason == "exact_duplicate" for item in report.candidates)
    assert {item.code for item in report.issues} == {"duplicate_candidate"}
    assert report.critical_issue_count == 0


def test_invalid_candidate_matrix_is_critical_and_inactive() -> None:
    invalid = (
        candidate(target_key="symbol:v1:python:function:missing", canonical_key="edge:v1:dangling"),
        candidate(relation_type="owns", canonical_key="edge:v1:invalid-relation"),
        candidate(source_spans=(), canonical_key="edge:v1:no-provenance"),
        candidate(
            origin="heuristic",
            support_type="heuristic_inferred",
            confidence=0.2,
            canonical_key="edge:v1:low-confidence",
        ),
        candidate(
            candidate_kind="node",
            node_type="function",
            label="run",
            canonical_key="node:v1:invalid-shape",
        ),
        candidate(repository_id="other_repo", canonical_key="edge:v1:wrong-owner"),
        candidate(candidate_kind="node", node_type="function", label="a", source_key=None, target_key=None, relation_type=None, canonical_key=SOURCE_KEY),
        candidate(candidate_kind="node", node_type="function", label="b", source_key=None, target_key=None, relation_type=None, canonical_key=SOURCE_KEY),
    )

    report = normalize(*invalid, minimum=0.5)
    codes = {item.code for item in report.issues}

    assert {
        "dangling_endpoint",
        "invalid_relation_type",
        "missing_provenance",
        "inferred_confidence_below_policy",
        "invalid_node_shape",
        "ownership_mismatch",
        "conflicting_canonical_key",
    } <= codes
    assert report.critical_issue_count >= 7
    assert not report.active_candidates


def test_normalization_is_byte_stable_under_input_order() -> None:
    first = candidate()
    second = candidate(
        canonical_key="edge:v1:called_by:stable",
        source_key=TARGET_KEY,
        target_key=SOURCE_KEY,
        relation_type="called_by",
    )

    assert normalize(first, second).to_json() == normalize(second, first).to_json()
