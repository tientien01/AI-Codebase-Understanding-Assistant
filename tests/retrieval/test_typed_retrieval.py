from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO
from app.services.index_models import ChunkRecord, EndpointRecord, FileRecord, RepositoryState, SymbolRecord
from app.services.retrieval import QuestionType, RetrievalRequest, RetrieverName
from app.services.retrieval.query_classifier import QueryClassifier
from app.services.retrieval.retrieval_service import RetrievalService


def repository_fixture(tmp_path: Path) -> RepositoryState:
    return RepositoryState(
        id="repo_retrieval",
        name="retrieval-fixture",
        source_type="upload_folder",
        source_uri=str(tmp_path),
        source_path=tmp_path,
        current_index_version=3,
        files=[
            FileRecord("backend/auth.py", tmp_path / "backend/auth.py", "python", "source", 120, "a" * 64),
            FileRecord("backend/cache.py", tmp_path / "backend/cache.py", "python", "source", 80, "b" * 64),
            FileRecord("docs/architecture.md", tmp_path / "docs/architecture.md", "markdown", "documentation", 90, "c" * 64),
        ],
        symbols=[SymbolRecord("symbol_authenticate", "authenticate_user", "function", "backend/auth.py", 1, 3)],
        endpoints=[EndpointRecord("POST", "/login", "authenticate_user", "backend/auth.py", 1, 3)],
        chunks=[
            ChunkRecord("chunk_auth", "backend/auth.py", "endpoint", "POST /login authenticates a user", 1, 3, "authenticate_user", content_hash="d" * 64),
            ChunkRecord("chunk_cache", "backend/cache.py", "function", "def load_cached_profile(): pass", 1, 1, "load_cached_profile", content_hash="e" * 64),
            ChunkRecord("chunk_arch", "docs/architecture.md", "file_summary", "System architecture and service boundaries", 1, 4, content_hash="f" * 64),
        ],
        graph_nodes=[
            GraphNodeDTO(id="node_auth", type="endpoint", label="POST /login", file_path="backend/auth.py", start_line=1, end_line=3),
            GraphNodeDTO(id="node_cache", type="function", label="load_cached_profile", file_path="backend/cache.py", start_line=1, end_line=1),
        ],
        graph_edges=[GraphEdgeDTO(source="node_auth", target="node_cache", type="calls", confidence=1.0)],
    )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("architecture overview", QuestionType.ARCHITECTURE_OVERVIEW),
        ("login flow hoat dong nhu the nao?", QuestionType.FLOW_TRACING),
        ("GET endpoint nao xu ly login?", QuestionType.API_QUESTION),
        ("database migration o dau?", QuestionType.DATABASE_QUESTION),
        ("loi 500 exception nay tu dau?", QuestionType.DEBUGGING),
        ("doc file nao cho onboarding?", QuestionType.ONBOARDING),
        ("neu sua auth thi impact gi?", QuestionType.IMPACT_ANALYSIS),
        ("authenticate_user o dau?", QuestionType.CODE_QUESTION),
    ],
)
def test_query_classifier_is_typed_deterministic_and_compatible(question: str, expected: QuestionType) -> None:
    classifier = QueryClassifier()

    first = classifier.classify(question)
    second = classifier.classify(question)

    assert first == second
    assert first.question_type is expected
    assert first.compatibility_label == expected.value
    assert first.reason_codes


def test_all_retrievers_emit_one_owned_candidate_contract(tmp_path: Path) -> None:
    repository = repository_fixture(tmp_path)
    service = RetrievalService()

    request, candidates = service.retrieve_candidates(
        repository,
        "POST /login backend/auth.py authenticate_user",
        limit=10,
    )

    assert request.repository_id == repository.id
    assert request.index_version_id == "idx_compat_3"
    assert {candidate.retriever for candidate in candidates} == set(RetrieverName)
    assert all(candidate.repository_id == request.repository_id for candidate in candidates)
    assert all(candidate.index_version_id == request.index_version_id for candidate in candidates)
    assert all(candidate.candidate_id.startswith("cand_") for candidate in candidates)
    assert len({candidate.candidate_id for candidate in candidates}) == len(candidates)
    assert all(candidate.reason_codes and candidate.entity_key and candidate.source_key for candidate in candidates)
    for retriever in RetrieverName:
        ranks = [candidate.rank for candidate in candidates if candidate.retriever is retriever]
        assert ranks == list(range(1, len(ranks) + 1))


def test_candidate_ids_and_hybrid_projection_are_repeatable(tmp_path: Path) -> None:
    repository = repository_fixture(tmp_path)
    service = RetrievalService()
    query = "POST /login backend/auth.py authenticate_user"

    _, first_candidates = service.retrieve_candidates(repository, query, limit=5)
    _, second_candidates = service.retrieve_candidates(repository, query, limit=5)
    first_matches = service.hybrid_search(repository, query, limit=5)
    second_matches = service.hybrid_search(repository, query, limit=5)

    assert [candidate.candidate_id for candidate in first_candidates] == [candidate.candidate_id for candidate in second_candidates]
    assert first_matches == second_matches
    assert [(match.chunk.id, match.retrieval_source) for match in first_matches] == [
        ("chunk_auth", "chunk"),
        ("chunk_cache", "graph"),
    ]


def test_graph_context_continues_graph_candidate_ranks(tmp_path: Path) -> None:
    service = RetrievalService()

    _, candidates = service.retrieve_candidates(repository_fixture(tmp_path), "login", limit=5)

    graph_candidates = [candidate for candidate in candidates if candidate.retriever is RetrieverName.GRAPH]
    assert [candidate.rank for candidate in graph_candidates] == list(range(1, len(graph_candidates) + 1))
    assert any(candidate.compatibility_source == "graph_context" for candidate in graph_candidates)


@pytest.mark.parametrize("query", ["", "the and how", "zzzzzz_nonexistent_token_987654"])
def test_empty_or_unrelated_query_preserves_insufficient_evidence(tmp_path: Path, query: str) -> None:
    service = RetrievalService()

    request, candidates = service.retrieve_candidates(repository_fixture(tmp_path), query, limit=5)

    assert request.query == query
    assert candidates == []
    assert service.hybrid_search(repository_fixture(tmp_path), query, limit=5) == []


def test_request_rejects_invalid_ownership_and_limit() -> None:
    classification = QueryClassifier().classify("code")

    with pytest.raises(ValueError, match="repository_id"):
        RetrievalRequest("", "idx_1", "code", 5, classification)
    with pytest.raises(ValueError, match="idx_"):
        RetrievalRequest("repo_1", "1", "code", 5, classification)
    with pytest.raises(ValueError, match="positive"):
        RetrievalRequest("repo_1", "idx_1", "code", 0, classification)


def test_retrieval_rejects_cross_repository_request(tmp_path: Path) -> None:
    repository = repository_fixture(tmp_path)
    service = RetrievalService()
    classification = service.classifier.classify("login")
    request = RetrievalRequest("repo_other", "idx_compat_3", "login", 5, classification)

    with pytest.raises(ValueError, match="ownership"):
        service.lexical_retriever.retrieve(request, repository)
