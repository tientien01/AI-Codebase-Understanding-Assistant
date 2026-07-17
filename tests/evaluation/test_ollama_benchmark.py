from __future__ import annotations

from dataclasses import replace

from app.services.evaluation.dataset import (
    CandidateObservation,
    EvaluationBudgets,
    EvaluationCase,
    EvaluationDataset,
    EvaluationPolicy,
    ExpectedResult,
)
from app.services.evaluation.ollama_benchmark import run_benchmark
from app.services.evaluation.ollama_embeddings import (
    EmbeddingBatch,
    EmbeddingModelIdentity,
    ModelMemory,
)
from app.services.retrieval.contracts import RetrieverName, SupportType


def candidate(
    candidate_id: str,
    *,
    entity_key: str,
    content: str,
    retriever: RetrieverName,
    rank: int,
) -> CandidateObservation:
    return CandidateObservation(
        candidate_id=candidate_id,
        retriever=retriever,
        retriever_version="test",
        entity_key=entity_key,
        source_key=f"file:v1:{candidate_id}.py",
        raw_score=1.0 / rank,
        rank=rank,
        matched_terms=(),
        reason_codes=("test",),
        support_type=SupportType.SOURCE_EXACT,
        provenance_refs=(f"prov_{candidate_id}",),
        source_path=f"{candidate_id}.py",
        content_hash="sha256:" + "a" * 64,
        start_line=1,
        end_line=1,
        chunk_type="function",
        chunk_content=content,
        title=candidate_id,
        result_type="function",
    )


def case(
    case_id: str,
    question: str,
    relevant: tuple[str, ...],
    candidates: tuple[CandidateObservation, ...],
    *,
    should_answer: bool = True,
) -> EvaluationCase:
    return EvaluationCase(
        id=case_id,
        schema_version="evaluation-case/v1",
        fixture_id="fixture_test",
        fixture_revision="sha256:" + "b" * 64,
        category="negative" if not should_answer else "semantic",
        question=question,
        expected=ExpectedResult(relevant, (), (), (), ()),
        policy=EvaluationPolicy(should_answer, (), ()),
        budgets=EvaluationBudgets(max_results=3, max_latency_ms=None, max_input_tokens=None),
        capability_preconditions=(),
        tags=(),
        candidates=candidates,
    )


def dataset() -> EvaluationDataset:
    exact_relevant = candidate(
        "cand_auth", entity_key="symbol:auth", content="auth login", retriever=RetrieverName.EXACT, rank=1
    )
    exact_other = candidate(
        "cand_db", entity_key="symbol:db", content="database schema", retriever=RetrieverName.LEXICAL, rank=2
    )
    semantic_relevant = candidate(
        "cand_token", entity_key="symbol:token", content="token signing", retriever=RetrieverName.SEMANTIC, rank=1
    )
    return EvaluationDataset(
        dataset_id="ret004-test",
        schema_version="evaluation-dataset/v1",
        dataset_revision="sha256:" + "c" * 64,
        fixture_id="fixture_test",
        fixture_revision="sha256:" + "b" * 64,
        repository_id="repo_test",
        files=(),
        cases=(
            case("exact-auth", "find auth", ("symbol:auth",), (exact_relevant, exact_other)),
            case(
                "semantic-token",
                "token purpose",
                ("symbol:token",),
                (semantic_relevant, exact_other),
            ),
            case("negative", "missing feature", (), (), should_answer=False),
        ),
        k_values=(1, 3),
        method_names=("exact_keyword", "naive_semantic", "deterministic_hybrid"),
    )


class FakeEmbeddingClient:
    def __init__(self, memory_bytes: int = 700_000_000) -> None:
        self.memory_bytes = memory_bytes

    def identity(self) -> EmbeddingModelIdentity:
        return EmbeddingModelIdentity(
            "embeddinggemma",
            "embeddinggemma:latest",
            "d" * 64,
            622_000_000,
            ("embedding",),
        )

    def embed(self, inputs: tuple[str, ...]) -> EmbeddingBatch:
        vectors = tuple(
            (1.0, 0.0)
            if "auth" in item or "token" in item
            else (0.0, 1.0)
            for item in inputs
        )
        return EmbeddingBatch(vectors, 2, 100, 0, len(inputs))

    def memory(self) -> ModelMemory:
        return ModelMemory(self.memory_bytes, 0, 2_048)


def test_benchmark_uses_same_inputs_records_three_runs_and_accepts_gain() -> None:
    report = run_benchmark(
        dataset(),
        FakeEmbeddingClient(),  # type: ignore[arg-type]
        repetitions=3,
        code_revision="RET-004-test",
        index_version_id="idx_ret_004_test",
        started_at="2026-07-17T00:00:00+00:00",
        completed_at="2026-07-17T00:01:00+00:00",
    )

    assert report["schema_version"] == "ollama-embedding-benchmark/v1"
    assert report["embedding_dimension"] == 2
    assert len(report["repetitions"]) == 3
    assert report["adoption"]["decision"] == "adopt_for_ret_005"
    first = report["repetitions"][0]["methods"]
    sparse_inputs = [item["candidate_input_ids"] for item in first["sparse"]["cases"]]
    assert sparse_inputs == [
        item["candidate_input_ids"] for item in first["ollama_dense"]["cases"]
    ]
    assert sparse_inputs == [
        item["candidate_input_ids"] for item in first["sparse_dense_hybrid"]["cases"]
    ]
    assert report["summary"]["provider_cost"] == 0
    assert report["report_checksum"].startswith("sha256:")


def test_benchmark_rejects_adoption_when_memory_budget_is_exceeded() -> None:
    report = run_benchmark(
        dataset(),
        FakeEmbeddingClient(memory_bytes=3 * 1024**3),  # type: ignore[arg-type]
        repetitions=3,
        code_revision="RET-004-test",
        index_version_id="idx_ret_004_test",
        started_at="2026-07-17T00:00:00+00:00",
        completed_at="2026-07-17T00:01:00+00:00",
    )

    assert report["adoption"]["decision"] == "do_not_adopt"
    assert report["adoption"]["checks"]["model_memory_within_budget"] is False


def test_benchmark_rejects_changed_candidate_identity() -> None:
    original = dataset()
    changed = replace(
        original.cases[1].candidates[1],
        chunk_content="changed content under reused candidate id",
    )
    invalid = replace(
        original,
        cases=(original.cases[0], replace(original.cases[1], candidates=(changed,))),
    )

    try:
        run_benchmark(
            invalid,
            FakeEmbeddingClient(),  # type: ignore[arg-type]
            repetitions=3,
            code_revision="RET-004-test",
            index_version_id="idx_ret_004_test",
            started_at="2026-07-17T00:00:00+00:00",
            completed_at="2026-07-17T00:01:00+00:00",
        )
    except ValueError as exc:
        assert "inconsistent observations" in str(exc)
    else:  # pragma: no cover - explicit failure keeps the assertion dependency-free.
        raise AssertionError("inconsistent candidate identity must fail closed")
