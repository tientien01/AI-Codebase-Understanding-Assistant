from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.schemas.api import CitationDTO, EvidenceDTO
from app.services.chat.agent_workflow_service import AgentWorkflowResult
from app.services.chat.chat_service import ChatService
from app.services.chat.citation_validation import (
    AnswerClaim,
    CitationValidationResult,
    ClaimCitationValidator,
    ClaimSupportLevel,
)
from app.services.chat.llm_client import LLMClient, LLMResult
from app.services.chat.sufficiency import SufficiencyAction, SufficiencyPolicy
from app.services.evidence.evidence_service import EvidenceService
from app.services.evidence.selection import (
    EvidenceContext,
    EvidenceContextStatus,
    ValidatedEvidenceBlock,
)
from app.services.index_models import FileRecord, RepositoryState
from app.services.retrieval.contracts import SupportType
from app.services.retrieval.retrieval_service import RetrievalService


class MemoryEvidenceStore:
    def __init__(self) -> None:
        self.evidence = {}

    def save_evidence(self, evidence) -> None:
        self.evidence[evidence.evidence_id] = evidence

    def get_evidence(self, evidence_id):
        return self.evidence.get(evidence_id)


def block(
    name: str,
    *,
    path: str | None = None,
    retrievers: tuple[str, ...] = ("lexical",),
    support: SupportType = SupportType.SOURCE_EXACT,
) -> ValidatedEvidenceBlock:
    return ValidatedEvidenceBlock(
        evidence_id=f"evidence_{name}",
        candidate_ids=(f"cand_{name}",),
        repository_id="repo_agent",
        index_version_id="idx_compat_1",
        ranking_config_id="rankcfg_test",
        source_key=f"file:v1:{path or name + '.py'}",
        entity_key=f"symbol:v1:{name}",
        file_path=path or f"{name}.py",
        start_line=1,
        end_line=1,
        symbol_name=name,
        source_type="code",
        source_sha256="1" * 64,
        chunk_sha256="2" * 64,
        support_type=support,
        retrievers=retrievers,
        reason_codes=("matched",),
        provenance_refs=(f"prov_{name}",),
        content=name,
        token_estimate=25,
        normalized_score=1.0,
    )


def context(*blocks: ValidatedEvidenceBlock) -> EvidenceContext:
    return EvidenceContext(
        repository_id="repo_agent",
        index_version_id="idx_compat_1",
        ranking_config_id="rankcfg_test",
        selected=tuple(blocks),
        rejected=(),
        omitted_summary=(),
        token_budget=100,
        used_tokens=sum(item.token_estimate for item in blocks),
        status=EvidenceContextStatus.READY if blocks else EvidenceContextStatus.INSUFFICIENT,
        truncation_reason=None,
        missing_requirements=(),
    )


def repository(tmp_path: Path) -> RepositoryState:
    source_path = tmp_path / "a.py"
    source_path.write_text("value = 1\n", encoding="utf-8")
    raw = source_path.read_bytes()
    return RepositoryState(
        id="repo_agent",
        name="agent",
        source_type="local",
        source_uri=None,
        source_path=tmp_path,
        status="ready",
        current_index_version=1,
        files=[
            FileRecord(
                path="a.py",
                absolute_path=source_path,
                language="python",
                file_type="source",
                size_bytes=len(raw),
                content_hash=hashlib.sha256(raw).hexdigest(),
            )
        ],
    )


def saved_evidence(*, stale: bool = False) -> EvidenceDTO:
    return EvidenceDTO(
        evidence_id="evidence_valid",
        repository_id="repo_agent",
        index_version=1,
        source_type="code",
        file_path="a.py",
        start_line=1,
        end_line=1,
        content_preview="value = 1",
        relevance_reason="matched",
        confidence_score=1.0,
        retrieval_source="exact",
        is_stale=stale,
    )


def citation(**changes) -> CitationDTO:
    values = {
        "evidence_id": "evidence_valid",
        "file_path": "a.py",
        "start_line": 1,
        "end_line": 1,
        "index_version": 1,
    }
    values.update(changes)
    return CitationDTO(**values)


def test_sufficiency_policy_is_question_specific_and_deterministic() -> None:
    policy = SufficiencyPolicy()

    direct = policy.evaluate("code_question", "value", context(block("a")), allow_repair=True)
    flow = policy.evaluate("flow_tracing", "flow", context(block("a")), allow_repair=True)
    repaired_flow = policy.evaluate(
        "flow_tracing",
        "flow",
        context(block("a", retrievers=("graph",)), block("b", retrievers=("graph",))),
        allow_repair=False,
    )
    architecture = policy.evaluate(
        "architecture_overview", "architecture", context(block("a"), block("b")), allow_repair=False
    )

    assert direct.action is SufficiencyAction.ANSWER
    assert flow.action is SufficiencyAction.REPAIR
    assert flow.repair_query == SufficiencyPolicy.repair_query("flow_tracing", "flow")
    assert repaired_flow.action is SufficiencyAction.ANSWER
    assert architecture.action is SufficiencyAction.ANSWER


def test_heuristic_only_support_cannot_confirm_a_claim() -> None:
    decision = SufficiencyPolicy().evaluate(
        "code_question",
        "value",
        context(block("a", support=SupportType.HEURISTIC)),
        allow_repair=False,
    )

    assert decision.action is SufficiencyAction.INSUFFICIENT
    assert decision.missing_requirements == ("required_strong_evidence_count:1",)


def test_valid_selected_current_citation_supports_claim(tmp_path: Path) -> None:
    state = repository(tmp_path)
    store = MemoryEvidenceStore()
    store.save_evidence(saved_evidence())
    validator = ClaimCitationValidator(EvidenceService(store))
    claim = AnswerClaim.from_answer(
        "The value is defined.", ("evidence_valid",), ClaimSupportLevel.DIRECT
    )

    result = validator.validate(state, (claim,), [citation()], ("evidence_valid",))

    assert result.valid is True
    assert result.validated_citation_ids == ("evidence_valid",)


@pytest.mark.parametrize(
    ("claim_ids", "selected", "citation_changes", "stale", "reason"),
    [
        (("evidence_valid", "evidence_valid"), ("evidence_valid",), {}, False, "duplicate_claim_citation"),
        (("evidence_valid",), (), {}, False, "citation_not_selected"),
        (("evidence_valid",), ("evidence_valid",), {"start_line": 2}, False, "citation_scope_mismatch"),
        (("evidence_valid",), ("evidence_valid",), {}, True, "stale_index_version"),
    ],
)
def test_invalid_claim_citation_mappings_fail_closed(
    tmp_path: Path,
    claim_ids: tuple[str, ...],
    selected: tuple[str, ...],
    citation_changes: dict[str, object],
    stale: bool,
    reason: str,
) -> None:
    state = repository(tmp_path)
    store = MemoryEvidenceStore()
    store.save_evidence(saved_evidence(stale=stale))
    validator = ClaimCitationValidator(EvidenceService(store))
    claim = AnswerClaim.from_answer("claim", claim_ids, ClaimSupportLevel.DIRECT)

    result = validator.validate(state, (claim,), [citation(**citation_changes)], selected)

    assert result.valid is False
    assert reason in result.items[0].reason_codes


def test_cross_repository_evidence_cannot_support_claim(tmp_path: Path) -> None:
    state = repository(tmp_path)
    store = MemoryEvidenceStore()
    foreign = saved_evidence().model_copy(update={"repository_id": "repo_other"})
    store.save_evidence(foreign)
    validator = ClaimCitationValidator(EvidenceService(store))
    claim = AnswerClaim.from_answer(
        "claim", ("evidence_valid",), ClaimSupportLevel.DIRECT
    )

    result = validator.validate(
        state, (claim,), [citation()], ("evidence_valid",)
    )

    assert result.valid is False
    assert "evidence_not_found" in result.items[0].reason_codes


def test_provider_response_parser_requires_declared_allowed_unique_citations() -> None:
    valid = LLMClient.parse_grounded_response(
        '{"answer":"Grounded","citation_ids":["evidence_a"]}',
        "openai",
        ("evidence_a",),
    )

    assert valid == LLMResult("Grounded", "openai", ("evidence_a",))
    assert LLMClient.parse_grounded_response("not json", "openai", ("evidence_a",)) is None
    assert LLMClient.parse_grounded_response(
        '{"answer":"Bad","citation_ids":["evidence_other"]}', "openai", ("evidence_a",)
    ) is None
    assert LLMClient.parse_grounded_response(
        '{"answer":"Bad","citation_ids":[]}', "openai", ("evidence_a",)
    ) is None


class FakeRepositories:
    def __init__(self, state) -> None:
        self.state = state

    def get_indexed_repository(self, repository_id):
        return self.state


class SpyLLM:
    def __init__(self) -> None:
        self.calls = 0

    def generate_grounded_answer(self, *args):
        self.calls += 1
        return LLMResult("provider", "fake", ("evidence_valid",))


class InsufficientAgent:
    def answer(self, state, message):
        return AgentWorkflowResult(
            question_type="code_question",
            answer="insufficient",
            citations=[citation()],
            evidence_sufficient=False,
            missing_evidence=["required_strong_evidence_count:1"],
        )


def test_chat_never_calls_provider_when_agent_evidence_is_insufficient(tmp_path: Path) -> None:
    state = repository(tmp_path)
    llm = SpyLLM()
    service = ChatService(
        FakeRepositories(state),  # type: ignore[arg-type]
        RetrievalService(),
        EvidenceService(MemoryEvidenceStore()),
        llm=llm,  # type: ignore[arg-type]
    )
    service.agent = InsufficientAgent()  # type: ignore[assignment]

    response = service.chat(state.id, "value")

    assert llm.calls == 0
    assert response.evidence_sufficient is False
    assert response.answer == "insufficient"
