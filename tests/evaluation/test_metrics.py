from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.evaluation.metrics import score_retrieval


@dataclass(frozen=True)
class Item:
    entity_key: str
    source_key: str
    start_line: int = 1
    end_line: int = 2


def test_metrics_match_hand_computed_binary_relevance() -> None:
    ranked = [
        Item("irrelevant", "file:a"),
        Item("expected:a", "file:b"),
        Item("expected:b", "file:c"),
    ]

    metrics = score_retrieval(
        ranked,
        frozenset({"expected:a", "expected:b"}),
        k=3,
        should_answer=True,
    )

    assert metrics.recall_at_k == 1.0
    assert metrics.precision_at_k == pytest.approx(2 / 3)
    assert metrics.reciprocal_rank == 0.5
    assert metrics.ndcg_at_k == pytest.approx(0.693426403617)
    assert metrics.exact_target_rank == 2
    assert metrics.source_diversity == 1.0
    assert metrics.duplicate_rate == 0.0
    assert metrics.insufficient_evidence_correct is None


def test_empty_negative_case_has_defined_insufficient_evidence_and_undefined_retrieval_quality() -> None:
    metrics = score_retrieval([], frozenset(), k=3, should_answer=False)

    assert metrics.recall_at_k is None
    assert metrics.precision_at_k is None
    assert metrics.reciprocal_rank is None
    assert metrics.ndcg_at_k is None
    assert metrics.exact_target_rank is None
    assert metrics.source_diversity == 0.0
    assert metrics.duplicate_rate == 0.0
    assert metrics.insufficient_evidence_correct == 1.0


def test_duplicate_span_and_false_answerability_are_measured_explicitly() -> None:
    ranked = [Item("expected", "file:a"), Item("expected", "file:a")]

    metrics = score_retrieval(ranked, frozenset({"expected"}), k=2, should_answer=False)

    assert metrics.recall_at_k == 1.0
    assert metrics.precision_at_k == 1.0
    assert metrics.duplicate_rate == 0.5
    assert metrics.insufficient_evidence_correct == 0.0


def test_duplicate_relevant_entity_cannot_inflate_ndcg_above_one() -> None:
    ranked = [Item("expected", "file:a"), Item("expected", "file:b")]

    metrics = score_retrieval(ranked, frozenset({"expected"}), k=2, should_answer=True)

    assert metrics.recall_at_k == 1.0
    assert metrics.ndcg_at_k == 1.0


def test_metric_k_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        score_retrieval([], frozenset(), k=0, should_answer=False)
