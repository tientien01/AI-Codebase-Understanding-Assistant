from __future__ import annotations

from dataclasses import dataclass
from math import log2
from typing import Protocol, Sequence


class RetrievedItem(Protocol):
    entity_key: str
    source_key: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class RetrievalMetrics:
    k: int
    recall_at_k: float | None
    precision_at_k: float | None
    reciprocal_rank: float | None
    ndcg_at_k: float | None
    exact_target_rank: int | None
    source_diversity: float
    duplicate_rate: float
    insufficient_evidence_correct: float | None

    def as_dict(self) -> dict[str, float | int | None]:
        return {
            "k": self.k,
            "recall_at_k": self.recall_at_k,
            "precision_at_k": self.precision_at_k,
            "reciprocal_rank": self.reciprocal_rank,
            "ndcg_at_k": self.ndcg_at_k,
            "exact_target_rank": self.exact_target_rank,
            "source_diversity": self.source_diversity,
            "duplicate_rate": self.duplicate_rate,
            "insufficient_evidence_correct": self.insufficient_evidence_correct,
        }


def _rounded(value: float) -> float:
    return round(value, 12)


def score_retrieval(
    ranked: Sequence[RetrievedItem],
    relevant_entity_keys: frozenset[str],
    *,
    k: int,
    should_answer: bool,
) -> RetrievalMetrics:
    """Score binary relevance; undefined positive metrics are represented by null."""

    if k <= 0:
        raise ValueError("metric k must be positive")
    top = list(ranked[:k])
    relevant_positions = [
        index for index, item in enumerate(top, start=1) if item.entity_key in relevant_entity_keys
    ]
    if relevant_entity_keys:
        hit_count = len({item.entity_key for item in top if item.entity_key in relevant_entity_keys})
        recall = _rounded(hit_count / len(relevant_entity_keys))
        precision = _rounded(sum(item.entity_key in relevant_entity_keys for item in top) / k)
        reciprocal_rank = _rounded(1 / relevant_positions[0]) if relevant_positions else 0.0
        dcg = sum(1 / log2(position + 1) for position in relevant_positions)
        ideal_count = min(len(relevant_entity_keys), k)
        ideal_dcg = sum(1 / log2(position + 1) for position in range(1, ideal_count + 1))
        ndcg = _rounded(dcg / ideal_dcg) if ideal_dcg else None
        exact_rank = relevant_positions[0] if relevant_positions else None
    else:
        recall = precision = reciprocal_rank = ndcg = None
        exact_rank = None

    owned_spans = [(item.source_key, item.start_line, item.end_line) for item in top]
    duplicate_rate = _rounded(1 - len(set(owned_spans)) / len(owned_spans)) if owned_spans else 0.0
    source_diversity = _rounded(len({item.source_key for item in top}) / len(top)) if top else 0.0
    insufficient = None if should_answer else float(not top)
    return RetrievalMetrics(
        k=k,
        recall_at_k=recall,
        precision_at_k=precision,
        reciprocal_rank=reciprocal_rank,
        ndcg_at_k=ndcg,
        exact_target_rank=exact_rank,
        source_diversity=source_diversity,
        duplicate_rate=duplicate_rate,
        insufficient_evidence_correct=insufficient,
    )
