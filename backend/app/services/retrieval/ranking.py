from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from math import isfinite

from app.services.retrieval.contracts import (
    RetrievalCandidate,
    RetrievalRequest,
    RetrieverName,
    SupportType,
)


class NormalizationMethod(str, Enum):
    RANK_ONLY = "rank_only"


class FusionMethod(str, Enum):
    RECIPROCAL_RANK = "reciprocal_rank"


class ScoreProjection(str, Enum):
    THEORETICAL_MAX = "theoretical_max"


class DeduplicationKey(str, Enum):
    OWNED_ENTITY_SOURCE_SPAN = "repository_index_entity_source_span"


class DiversityPolicy(str, Enum):
    NONE = "none"


@dataclass(frozen=True)
class RetrieverPolicy:
    retriever: RetrieverName
    enabled: bool = True
    candidate_limit: int = 50
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.retriever, RetrieverName):
            raise ValueError("retriever policy name must be controlled")
        if self.candidate_limit <= 0:
            raise ValueError("retriever candidate_limit must be positive")
        if not isfinite(self.weight) or self.weight <= 0:
            raise ValueError("retriever weight must be finite and positive")


@dataclass(frozen=True)
class ReasonBoost:
    reason_code: str
    multiplier: float

    def __post_init__(self) -> None:
        if not self.reason_code.strip():
            raise ValueError("boost reason_code must not be blank")
        if not isfinite(self.multiplier) or self.multiplier <= 0:
            raise ValueError("boost multiplier must be finite and positive")


@dataclass(frozen=True)
class RankingConfiguration:
    policies: tuple[RetrieverPolicy, ...]
    allowed_support_types: tuple[SupportType, ...]
    rrf_k: int = 60
    final_limit: int = 20
    context_token_budget: int = 8_000
    normalization_method: NormalizationMethod = NormalizationMethod.RANK_ONLY
    fusion_method: FusionMethod = FusionMethod.RECIPROCAL_RANK
    score_projection: ScoreProjection = ScoreProjection.THEORETICAL_MAX
    deduplication_key: DeduplicationKey = DeduplicationKey.OWNED_ENTITY_SOURCE_SPAN
    diversity_policy: DiversityPolicy = DiversityPolicy.NONE
    reason_boosts: tuple[ReasonBoost, ...] = ()
    schema_version: str = "ranking-config/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "ranking-config/v1":
            raise ValueError("unsupported ranking configuration schema")
        if not self.policies:
            raise ValueError("ranking configuration requires retriever policies")
        if not isinstance(self.normalization_method, NormalizationMethod):
            raise ValueError("unsupported normalization method")
        if not isinstance(self.fusion_method, FusionMethod):
            raise ValueError("unsupported fusion method")
        if not isinstance(self.score_projection, ScoreProjection):
            raise ValueError("unsupported score projection")
        if not isinstance(self.deduplication_key, DeduplicationKey):
            raise ValueError("unsupported deduplication key")
        if not isinstance(self.diversity_policy, DiversityPolicy):
            raise ValueError("unsupported diversity policy")
        policy_names = [policy.retriever for policy in self.policies]
        if len(policy_names) != len(set(policy_names)):
            raise ValueError("ranking configuration contains duplicate retriever policies")
        if set(policy_names) != set(RetrieverName):
            raise ValueError("ranking configuration must declare every controlled retriever")
        if not any(policy.enabled for policy in self.policies):
            raise ValueError("ranking configuration must enable at least one retriever")
        if not self.allowed_support_types or len(self.allowed_support_types) != len(set(self.allowed_support_types)):
            raise ValueError("allowed support types must be non-empty and unique")
        if any(not isinstance(item, SupportType) for item in self.allowed_support_types):
            raise ValueError("allowed support types must be controlled")
        if self.rrf_k <= 0 or self.final_limit <= 0 or self.context_token_budget <= 0:
            raise ValueError("rrf_k, final_limit, and context_token_budget must be positive")
        boost_reasons = [boost.reason_code for boost in self.reason_boosts]
        if len(boost_reasons) != len(set(boost_reasons)):
            raise ValueError("ranking configuration contains duplicate reason boosts")

    @property
    def config_id(self) -> str:
        digest = hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()[:24]
        return f"rankcfg_{digest}"

    def canonical_json(self) -> str:
        payload = {
            "allowed_support_types": sorted(item.value for item in self.allowed_support_types),
            "context_token_budget": self.context_token_budget,
            "deduplication_key": self.deduplication_key.value,
            "diversity_policy": self.diversity_policy.value,
            "final_limit": self.final_limit,
            "fusion_method": self.fusion_method.value,
            "normalization_method": self.normalization_method.value,
            "policies": [
                {
                    "candidate_limit": policy.candidate_limit,
                    "enabled": policy.enabled,
                    "retriever": policy.retriever.value,
                    "weight": policy.weight,
                }
                for policy in sorted(self.policies, key=lambda item: item.retriever.value)
            ],
            "reason_boosts": [
                {"multiplier": boost.multiplier, "reason_code": boost.reason_code}
                for boost in sorted(self.reason_boosts, key=lambda item: item.reason_code)
            ],
            "rrf_k": self.rrf_k,
            "schema_version": self.schema_version,
            "score_projection": self.score_projection.value,
        }
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    def policy_by_retriever(self) -> dict[RetrieverName, RetrieverPolicy]:
        return {policy.retriever: policy for policy in self.policies}


@dataclass(frozen=True)
class RankingContribution:
    retriever: RetrieverName
    rank: int
    weight: float
    reciprocal_rank_score: float
    candidate_id: str


@dataclass(frozen=True)
class RankedCandidate:
    ranking_config_id: str
    candidate: RetrievalCandidate
    candidate_ids: tuple[str, ...]
    retrievers: tuple[RetrieverName, ...]
    contributions: tuple[RankingContribution, ...]
    fused_score: float
    normalized_score: float
    best_rank: int
    support_type: SupportType
    matched_terms: tuple[str, ...]
    reason_codes: tuple[str, ...]
    provenance_refs: tuple[str, ...]


SUPPORT_ORDER = {
    SupportType.SOURCE_EXACT: 0,
    SupportType.STATIC_RESOLVED: 1,
    SupportType.HEURISTIC: 2,
}


class ReciprocalRankRanker:
    """Deterministic rank-only fusion over owned RET-001 candidates."""

    def __init__(self, configuration: RankingConfiguration) -> None:
        self.configuration = configuration

    def rank(
        self,
        request: RetrievalRequest,
        candidates: list[RetrievalCandidate],
    ) -> list[RankedCandidate]:
        policies = self.configuration.policy_by_retriever()
        filtered: list[RetrievalCandidate] = []
        for candidate in candidates:
            candidate.validate_ownership(request)
            policy = policies[candidate.retriever]
            if not policy.enabled or candidate.rank > policy.candidate_limit:
                continue
            if candidate.support_type not in self.configuration.allowed_support_types:
                continue
            filtered.append(candidate)

        groups: dict[tuple[str, str, str, str, int, int], list[RetrievalCandidate]] = {}
        for candidate in filtered:
            key = (
                candidate.repository_id,
                candidate.index_version_id,
                candidate.entity_key,
                candidate.source_key,
                candidate.chunk.start_line,
                candidate.chunk.end_line,
            )
            groups.setdefault(key, []).append(candidate)

        theoretical_max = sum(
            policy.weight / (self.configuration.rrf_k + 1)
            for policy in policies.values()
            if policy.enabled
        )
        ranked = [
            self._fuse_group(group, policies, theoretical_max)
            for _, group in sorted(groups.items())
        ]
        ranked.sort(
            key=lambda item: (
                -item.fused_score,
                SUPPORT_ORDER[item.support_type],
                item.best_rank,
                item.candidate.entity_key,
                item.candidate.candidate_id,
            )
        )
        return ranked[: min(request.limit, self.configuration.final_limit)]

    def _fuse_group(
        self,
        group: list[RetrievalCandidate],
        policies: dict[RetrieverName, RetrieverPolicy],
        theoretical_max: float,
    ) -> RankedCandidate:
        by_retriever: dict[RetrieverName, RetrievalCandidate] = {}
        for candidate in sorted(group, key=lambda item: (item.rank, item.candidate_id)):
            by_retriever.setdefault(candidate.retriever, candidate)

        contributions = tuple(
            RankingContribution(
                retriever=retriever,
                rank=candidate.rank,
                weight=policies[retriever].weight,
                reciprocal_rank_score=policies[retriever].weight / (
                    self.configuration.rrf_k + candidate.rank
                ),
                candidate_id=candidate.candidate_id,
            )
            for retriever, candidate in sorted(by_retriever.items(), key=lambda item: item[0].value)
        )
        fused_score = sum(contribution.reciprocal_rank_score for contribution in contributions)
        reason_codes = tuple(sorted({reason for candidate in group for reason in candidate.reason_codes}))
        boost_multiplier = 1.0
        for boost in self.configuration.reason_boosts:
            if boost.reason_code in reason_codes:
                boost_multiplier *= boost.multiplier
        fused_score = round(fused_score * boost_multiplier, 12)
        normalized_score = round(min(1.0, fused_score / theoretical_max), 12)
        support_type = min((candidate.support_type for candidate in group), key=SUPPORT_ORDER.__getitem__)
        representative = min(
            group,
            key=lambda item: (
                SUPPORT_ORDER[item.support_type],
                item.rank,
                item.entity_key,
                item.candidate_id,
            ),
        )
        return RankedCandidate(
            ranking_config_id=self.configuration.config_id,
            candidate=representative,
            candidate_ids=tuple(sorted(candidate.candidate_id for candidate in group)),
            retrievers=tuple(sorted(by_retriever, key=lambda item: item.value)),
            contributions=contributions,
            fused_score=fused_score,
            normalized_score=normalized_score,
            best_rank=min(candidate.rank for candidate in group),
            support_type=support_type,
            matched_terms=tuple(sorted({term for candidate in group for term in candidate.matched_terms})),
            reason_codes=reason_codes,
            provenance_refs=tuple(sorted({ref for candidate in group for ref in candidate.provenance_refs})),
        )


def default_ranking_configuration() -> RankingConfiguration:
    return RankingConfiguration(
        policies=tuple(RetrieverPolicy(retriever) for retriever in RetrieverName),
        allowed_support_types=tuple(SupportType),
    )
