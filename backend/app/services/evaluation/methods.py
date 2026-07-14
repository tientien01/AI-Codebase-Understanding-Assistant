from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
from typing import Iterable

from app.services.evaluation.dataset import EvaluationCase, canonical_json
from app.services.retrieval.contracts import (
    QuestionType,
    QueryClassification,
    RetrievalCandidate,
    RetrievalRequest,
    RetrieverName,
)
from app.services.retrieval.ranking import (
    RankingConfiguration,
    ReciprocalRankRanker,
    default_ranking_configuration,
)


class EvaluationMethod(str, Enum):
    EXACT_KEYWORD = "exact_keyword"
    NAIVE_SEMANTIC = "naive_semantic"
    DETERMINISTIC_HYBRID = "deterministic_hybrid"


@dataclass(frozen=True)
class EvaluationResultItem:
    entity_key: str
    source_key: str
    start_line: int
    end_line: int
    candidate_ids: tuple[str, ...]
    retrievers: tuple[str, ...]
    score: float

    def as_dict(self) -> dict[str, object]:
        return {
            "entity_key": self.entity_key,
            "source_key": self.source_key,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "candidate_ids": list(self.candidate_ids),
            "retrievers": list(self.retrievers),
            "score": self.score,
        }


@dataclass(frozen=True)
class MethodResult:
    method: EvaluationMethod
    method_config_id: str
    status: str
    results: tuple[EvaluationResultItem, ...]
    error_code: str | None = None


def _request(case: EvaluationCase, repository_id: str, index_version_id: str) -> RetrievalRequest:
    return RetrievalRequest(
        repository_id=repository_id,
        index_version_id=index_version_id,
        query=case.question,
        limit=case.budgets.max_results,
        classification=QueryClassification(
            question_type=QuestionType.CODE_QUESTION,
            confidence=1.0,
            reason_codes=(f"evaluation:{case.category}",),
        ),
    )


def _configuration_for(retrievers: frozenset[RetrieverName]) -> RankingConfiguration:
    baseline = default_ranking_configuration()
    policies = tuple(
        replace(policy, enabled=policy.retriever in retrievers) for policy in baseline.policies
    )
    return replace(baseline, policies=policies)


def _ranked_items(
    request: RetrievalRequest,
    candidates: list[RetrievalCandidate],
    configuration: RankingConfiguration,
) -> tuple[EvaluationResultItem, ...]:
    ranked = ReciprocalRankRanker(configuration).rank(request, candidates)
    return tuple(
        EvaluationResultItem(
            entity_key=item.candidate.entity_key,
            source_key=item.candidate.source_key,
            start_line=item.candidate.chunk.start_line,
            end_line=item.candidate.chunk.end_line,
            candidate_ids=item.candidate_ids,
            retrievers=tuple(retriever.value for retriever in item.retrievers),
            score=item.normalized_score,
        )
        for item in ranked
    )


def _naive_semantic_items(candidates: Iterable[RetrievalCandidate], limit: int) -> tuple[EvaluationResultItem, ...]:
    semantic = sorted(
        (item for item in candidates if item.retriever is RetrieverName.SEMANTIC),
        key=lambda item: (item.rank, item.candidate_id),
    )
    seen: set[tuple[str, str, int, int]] = set()
    output: list[EvaluationResultItem] = []
    for item in semantic:
        key = (item.entity_key, item.source_key, item.chunk.start_line, item.chunk.end_line)
        if key in seen:
            continue
        seen.add(key)
        output.append(
            EvaluationResultItem(
                entity_key=item.entity_key,
                source_key=item.source_key,
                start_line=item.chunk.start_line,
                end_line=item.chunk.end_line,
                candidate_ids=(item.candidate_id,),
                retrievers=(RetrieverName.SEMANTIC.value,),
                score=item.raw_score,
            )
        )
        if len(output) == limit:
            break
    return tuple(output)


def _naive_config_id(limit: int) -> str:
    payload = {"schema_version": "evaluation-method/v1", "method": "naive_semantic", "top_k": limit}
    return f"evalcfg_{hashlib.sha256(canonical_json(payload).encode('utf-8')).hexdigest()[:24]}"


def evaluate_method(
    method: EvaluationMethod,
    case: EvaluationCase,
    *,
    repository_id: str,
    index_version_id: str,
) -> MethodResult:
    request = _request(case, repository_id, index_version_id)
    candidates = [item.to_candidate(repository_id, index_version_id) for item in case.candidates]
    if method is EvaluationMethod.NAIVE_SEMANTIC:
        return MethodResult(
            method=method,
            method_config_id=_naive_config_id(request.limit),
            status="completed",
            results=_naive_semantic_items(candidates, request.limit),
        )
    if method is EvaluationMethod.EXACT_KEYWORD:
        configuration = _configuration_for(
            frozenset(
                {
                    RetrieverName.EXACT,
                    RetrieverName.LEXICAL,
                    RetrieverName.SYMBOL,
                    RetrieverName.ENDPOINT,
                }
            )
        )
    elif method is EvaluationMethod.DETERMINISTIC_HYBRID:
        configuration = default_ranking_configuration()
    else:  # pragma: no cover - Enum prevents this for typed callers.
        raise ValueError("unsupported evaluation method")
    return MethodResult(
        method=method,
        method_config_id=configuration.config_id,
        status="completed",
        results=_ranked_items(request, candidates, configuration),
    )
