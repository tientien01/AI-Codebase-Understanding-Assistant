from __future__ import annotations

from dataclasses import replace

import pytest

from app.services.index_models import ChunkRecord
from app.services.retrieval import QuestionType, QueryClassification, RetrievalCandidate, RetrievalRequest, RetrieverName, SupportType
from app.services.retrieval.ranking import (
    RankingConfiguration,
    ReasonBoost,
    ReciprocalRankRanker,
    RetrieverPolicy,
    default_ranking_configuration,
)


def request(limit: int = 10) -> RetrievalRequest:
    return RetrievalRequest(
        repository_id="repo_rank",
        index_version_id="idx_rank_1",
        query="login",
        limit=limit,
        classification=QueryClassification(QuestionType.CODE_QUESTION, 0.5, ("default:code_question",)),
    )


def candidate(
    name: str,
    retriever: RetrieverName,
    rank: int,
    raw_score: float,
    *,
    entity: str | None = None,
    source: str | None = None,
    support: SupportType = SupportType.SOURCE_EXACT,
    reason: str = "matched",
    repository_id: str = "repo_rank",
    index_version_id: str = "idx_rank_1",
) -> RetrievalCandidate:
    chunk = ChunkRecord(
        id=f"chunk_{name}",
        file_path=f"src/{name}.py",
        chunk_type="function",
        content=f"def {name}(): pass",
        start_line=1,
        end_line=1,
        symbol_name=name,
        content_hash=name.ljust(64, "0")[:64],
    )
    return RetrievalCandidate(
        candidate_id=f"cand_{name}_{retriever.value}_{rank}",
        repository_id=repository_id,
        index_version_id=index_version_id,
        retriever=retriever,
        retriever_version="1",
        entity_key=entity or f"symbol:v1:{name}",
        source_key=source or f"file:v1:src/{name}.py",
        raw_score=raw_score,
        rank=rank,
        matched_terms=("login",),
        reason_codes=(reason,),
        support_type=support,
        provenance_refs=(f"prov_{name}",),
        chunk=chunk,
        result_type="function",
        title=name,
        compatibility_source=retriever.value,
    )


def configuration_with(
    *,
    policies: tuple[RetrieverPolicy, ...] | None = None,
    allowed_support_types: tuple[SupportType, ...] | None = None,
    final_limit: int = 20,
    reason_boosts: tuple[ReasonBoost, ...] = (),
) -> RankingConfiguration:
    baseline = default_ranking_configuration()
    return RankingConfiguration(
        policies=policies or baseline.policies,
        allowed_support_types=allowed_support_types or baseline.allowed_support_types,
        final_limit=final_limit,
        reason_boosts=reason_boosts,
    )


def test_default_configuration_is_canonical_content_addressed_and_complete() -> None:
    first = default_ranking_configuration()
    second = default_ranking_configuration()

    assert first.config_id == second.config_id
    assert first.config_id.startswith("rankcfg_")
    assert first.canonical_json() == second.canonical_json()
    assert {policy.retriever for policy in first.policies} == set(RetrieverName)
    assert '"fusion_method":"reciprocal_rank"' in first.canonical_json()
    assert '"normalization_method":"rank_only"' in first.canonical_json()


def test_configuration_identity_changes_with_every_ranking_policy_field() -> None:
    baseline = default_ranking_configuration()
    changed_policy = tuple(
        replace(policy, weight=2.0) if policy.retriever is RetrieverName.EXACT else policy
        for policy in baseline.policies
    )

    assert configuration_with(policies=changed_policy).config_id != baseline.config_id
    assert configuration_with(final_limit=5).config_id != baseline.config_id
    assert configuration_with(reason_boosts=(ReasonBoost("exact_named_target", 1.1),)).config_id != baseline.config_id


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RetrieverPolicy(RetrieverName.EXACT, candidate_limit=0),
        lambda: RetrieverPolicy(RetrieverName.EXACT, weight=float("nan")),
        lambda: RankingConfiguration((), tuple(SupportType)),
        lambda: RankingConfiguration(tuple(RetrieverPolicy(RetrieverName.EXACT) for _ in RetrieverName), tuple(SupportType)),
        lambda: RankingConfiguration(tuple(RetrieverPolicy(item) for item in RetrieverName), ()),
        lambda: RankingConfiguration(tuple(RetrieverPolicy(item) for item in RetrieverName), tuple(SupportType), rrf_k=0),
        lambda: replace(default_ranking_configuration(), normalization_method="unknown"),
        lambda: replace(default_ranking_configuration(), fusion_method="unknown"),
        lambda: replace(default_ranking_configuration(), allowed_support_types=("unknown",)),
    ],
)
def test_invalid_configuration_fails_closed(factory) -> None:
    with pytest.raises(ValueError):
        factory()


def test_weighted_rrf_matches_hand_calculation_and_merges_duplicate_span() -> None:
    ranker = ReciprocalRankRanker(default_ranking_configuration())
    lexical = candidate("login", RetrieverName.LEXICAL, 1, 100.0, reason="lexical")
    semantic = candidate("login", RetrieverName.SEMANTIC, 2, 0.01, reason="semantic", support=SupportType.HEURISTIC)

    result = ranker.rank(request(), [semantic, lexical])

    assert len(result) == 1
    expected = round(1 / 61 + 1 / 62, 12)
    assert result[0].fused_score == pytest.approx(expected)
    assert result[0].retrievers == (RetrieverName.LEXICAL, RetrieverName.SEMANTIC)
    assert result[0].support_type is SupportType.SOURCE_EXACT
    assert result[0].reason_codes == ("lexical", "semantic")
    assert result[0].matched_terms == ("login",)
    assert result[0].provenance_refs == ("prov_login",)
    assert 0 < result[0].normalized_score <= 1


def test_ranking_is_invariant_to_input_order_and_raw_score_scale() -> None:
    ranker = ReciprocalRankRanker(default_ranking_configuration())
    original = [
        candidate("a", RetrieverName.LEXICAL, 1, 1.0),
        candidate("a", RetrieverName.SEMANTIC, 2, 10_000.0),
        candidate("b", RetrieverName.LEXICAL, 2, 50_000.0),
        candidate("b", RetrieverName.SEMANTIC, 1, 0.001),
    ]
    rescaled = [replace(item, raw_score=item.raw_score * 137.0) for item in reversed(original)]

    first = ranker.rank(request(), original)
    second = ranker.rank(request(), rescaled)

    assert [(item.candidate.entity_key, item.fused_score) for item in first] == [
        (item.candidate.entity_key, item.fused_score) for item in second
    ]
    assert [item.candidate.entity_key for item in first] == ["symbol:v1:a", "symbol:v1:b"]


def test_filters_apply_before_fusion_and_enforce_per_retriever_limit() -> None:
    baseline = default_ranking_configuration()
    policies = tuple(
        replace(policy, enabled=False) if policy.retriever is RetrieverName.SEMANTIC
        else replace(policy, candidate_limit=1) if policy.retriever is RetrieverName.LEXICAL
        else policy
        for policy in baseline.policies
    )
    ranker = ReciprocalRankRanker(
        configuration_with(policies=policies, allowed_support_types=(SupportType.SOURCE_EXACT,))
    )
    candidates = [
        candidate("kept", RetrieverName.LEXICAL, 1, 1.0),
        candidate("over_limit", RetrieverName.LEXICAL, 2, 100.0),
        candidate("disabled", RetrieverName.SEMANTIC, 1, 100.0),
        candidate("support", RetrieverName.GRAPH, 1, 100.0, support=SupportType.STATIC_RESOLVED),
    ]

    result = ranker.rank(request(), candidates)

    assert [item.candidate.entity_key for item in result] == ["symbol:v1:kept"]


def test_cross_repository_or_index_candidate_is_rejected() -> None:
    ranker = ReciprocalRankRanker(default_ranking_configuration())

    with pytest.raises(ValueError, match="ownership"):
        ranker.rank(request(), [candidate("wrong_repo", RetrieverName.LEXICAL, 1, 1.0, repository_id="repo_other")])
    with pytest.raises(ValueError, match="ownership"):
        ranker.rank(request(), [candidate("wrong_index", RetrieverName.LEXICAL, 1, 1.0, index_version_id="idx_other")])


def test_tie_order_prefers_support_then_rank_then_entity_and_id() -> None:
    ranker = ReciprocalRankRanker(default_ranking_configuration())
    candidates = [
        candidate("heuristic", RetrieverName.SEMANTIC, 1, 1.0, support=SupportType.HEURISTIC),
        candidate("z_exact", RetrieverName.LEXICAL, 1, 1.0),
        candidate("a_exact", RetrieverName.LEXICAL, 1, 1.0),
    ]

    result = ranker.rank(request(), candidates)

    assert [item.candidate.entity_key for item in result] == [
        "symbol:v1:a_exact",
        "symbol:v1:z_exact",
        "symbol:v1:heuristic",
    ]


def test_final_limit_is_bounded_by_request_and_configuration() -> None:
    ranker = ReciprocalRankRanker(configuration_with(final_limit=2))
    candidates = [candidate(str(index), RetrieverName.LEXICAL, index, 1.0) for index in range(1, 6)]

    assert len(ranker.rank(request(limit=5), candidates)) == 2
    assert len(ranker.rank(request(limit=1), candidates)) == 1


def test_declared_reason_boost_is_deterministic_and_bounded() -> None:
    configuration = configuration_with(reason_boosts=(ReasonBoost("exact_named_target", 1.2),))
    ranker = ReciprocalRankRanker(configuration)

    plain = ranker.rank(request(), [candidate("plain", RetrieverName.EXACT, 1, 1.0)])[0]
    boosted = ranker.rank(
        request(),
        [candidate("boosted", RetrieverName.EXACT, 1, 1.0, reason="exact_named_target")],
    )[0]

    assert boosted.fused_score == pytest.approx(round(plain.fused_score * 1.2, 12))
    assert 0 < boosted.normalized_score <= 1
