from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from app.services.evidence.evidence_service import EvidenceService
from app.services.evidence.selection import (
    EvidenceContextStatus,
    EvidenceSelectionPolicy,
    EvidenceSelector,
)
from app.services.index_models import ChunkRecord, FileRecord, RepositoryState
from app.services.chat.agent_workflow_service import AgentWorkflowService
from app.services.retrieval.contracts import (
    QueryClassification,
    QuestionType,
    RetrievalCandidate,
    RetrievalRequest,
    RetrieverName,
    SupportType,
)
from app.services.retrieval.ranking import ReciprocalRankRanker, default_ranking_configuration
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.text_utils import content_hash


class MemoryEvidenceStore:
    def __init__(self) -> None:
        self.evidence = {}

    def save_evidence(self, evidence) -> None:
        self.evidence[evidence.evidence_id] = evidence

    def get_evidence(self, evidence_id):
        return self.evidence.get(evidence_id)


def repository_with_files(tmp_path: Path, contents: dict[str, str]) -> RepositoryState:
    repository = RepositoryState(
        id="repo_evidence",
        name="evidence",
        source_type="local",
        source_uri=None,
        source_path=tmp_path,
        status="ready",
        current_index_version=1,
    )
    for relative_path, source in contents.items():
        absolute_path = tmp_path / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_text(source, encoding="utf-8")
        raw = absolute_path.read_bytes()
        repository.files.append(
            FileRecord(
                path=relative_path,
                absolute_path=absolute_path,
                language="python",
                file_type="source",
                size_bytes=len(raw),
                content_hash=hashlib.sha256(raw).hexdigest(),
            )
        )
    return repository


def request(question_type: QuestionType = QuestionType.CODE_QUESTION, limit: int = 6) -> RetrievalRequest:
    return RetrievalRequest(
        repository_id="repo_evidence",
        index_version_id="idx_compat_1",
        query="target",
        limit=limit,
        classification=QueryClassification(question_type, 1.0, ("test",)),
    )


def candidate(
    repository: RepositoryState,
    relative_path: str,
    *,
    name: str,
    rank: int,
    retriever: RetrieverName = RetrieverName.LEXICAL,
    support: SupportType = SupportType.SOURCE_EXACT,
    start_line: int = 1,
    end_line: int = 1,
    content: str | None = None,
    reason: str = "lexical_match",
) -> RetrievalCandidate:
    source_lines = next(item for item in repository.files if item.path == relative_path).absolute_path.read_text(
        encoding="utf-8"
    ).splitlines()
    chunk_content = content if content is not None else "\n".join(source_lines[start_line - 1 : end_line]).strip()
    chunk_hash = content_hash(f"{relative_path}:{start_line}:{end_line}:{chunk_content.strip()}")
    chunk = ChunkRecord(
        id=f"chunk_{name}",
        file_path=relative_path,
        chunk_type="function",
        content=chunk_content,
        start_line=start_line,
        end_line=end_line,
        symbol_name=name,
        content_hash=chunk_hash,
    )
    return RetrievalCandidate(
        candidate_id=f"cand_{name}_{retriever.value}_{rank}",
        repository_id=repository.id,
        index_version_id="idx_compat_1",
        retriever=retriever,
        retriever_version="1",
        entity_key=f"symbol:v1:{name}",
        source_key=f"file:v1:{relative_path}",
        raw_score=1.0,
        rank=rank,
        matched_terms=("target",),
        reason_codes=(reason,),
        support_type=support,
        provenance_refs=(f"provenance:{name}",),
        chunk=chunk,
        result_type="function",
        title=name,
        compatibility_source=retriever.value,
    )


def ranked(req: RetrievalRequest, candidates: list[RetrievalCandidate]):
    return ReciprocalRankRanker(default_ranking_configuration()).rank(req, candidates)


def test_valid_selection_is_stable_whole_and_persists_owned_metadata(tmp_path: Path) -> None:
    repository = repository_with_files(tmp_path, {"src/a.py": "def target():\n    return 1\n"})
    req = request()
    results = ranked(req, [candidate(repository, "src/a.py", name="target", rank=1, end_line=2)])
    policy = EvidenceSelectionPolicy(token_budget=200, max_evidence=3)
    selector = EvidenceSelector()

    first = selector.select(repository, req, results, policy)
    second = selector.select(repository, req, list(reversed(results)), policy)

    assert first == second
    assert first.status is EvidenceContextStatus.READY
    assert first.selected[0].evidence_id.startswith("evidence_")
    assert first.selected[0].content == "def target():\n    return 1"
    assert first.used_tokens == first.selected[0].token_estimate
    assert first.used_tokens == 24 + 7

    store = MemoryEvidenceStore()
    service = EvidenceService(store)
    citations = service.context_to_citations(repository, first)
    service.context_to_citations(repository, first)

    assert len(store.evidence) == 1
    assert citations[0].evidence_id == first.selected[0].evidence_id
    saved = store.evidence[citations[0].evidence_id]
    assert saved.metadata["index_version_id"] == "idx_compat_1"
    assert saved.metadata["source_sha256"] == repository.files[0].content_hash
    assert saved.metadata["support_type"] == "source_exact"
    assert saved.metadata["ranking_config_id"].startswith("rankcfg_")


def test_stale_index_is_explicitly_insufficient(tmp_path: Path) -> None:
    repository = repository_with_files(tmp_path, {"a.py": "target = 1\n"})
    req = request()
    results = ranked(req, [candidate(repository, "a.py", name="target", rank=1)])
    stale_request = replace(req, index_version_id="idx_compat_0")
    stale_results = [replace(item, candidate=replace(item.candidate, index_version_id="idx_compat_0")) for item in results]

    context = EvidenceSelector().select(
        repository, stale_request, stale_results, EvidenceSelectionPolicy(100, 2)
    )

    assert context.status is EvidenceContextStatus.INSUFFICIENT
    assert not context.selected
    assert {item.reason_code for item in context.rejected} == {"stale_index_version"}
    assert context.missing_requirements == ("required_evidence_count:1",)


def test_cross_owner_candidate_fails_closed(tmp_path: Path) -> None:
    repository = repository_with_files(tmp_path, {"a.py": "target = 1\n"})
    req = request()
    results = ranked(req, [candidate(repository, "a.py", name="target", rank=1)])
    wrong = replace(results[0], candidate=replace(results[0].candidate, repository_id="repo_other"))

    with pytest.raises(ValueError, match="ownership"):
        EvidenceSelector().select(repository, req, [wrong], EvidenceSelectionPolicy(100, 2))


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing", "source_missing"),
        ("changed", "source_hash_changed"),
        ("range", "range_invalid"),
        ("chunk_hash", "chunk_hash_changed"),
        ("blocked", "blocked_source"),
        ("support", "unsupported_support_type"),
    ],
)
def test_invalid_sources_are_rejected_with_stable_reason(
    tmp_path: Path, mutation: str, reason: str
) -> None:
    repository = repository_with_files(tmp_path, {"a.py": "target = 1\n"})
    req = request()
    item = candidate(repository, "a.py", name="target", rank=1)
    if mutation == "missing":
        repository.files[0].absolute_path.unlink()
    elif mutation == "changed":
        repository.files[0].absolute_path.write_text("changed = 2\n", encoding="utf-8")
    elif mutation == "range":
        item = replace(item, chunk=replace(item.chunk, end_line=2))
    elif mutation == "chunk_hash":
        item = replace(item, chunk=replace(item.chunk, content_hash="0" * 64))
    elif mutation == "blocked":
        repository.skipped_file_records.append({"file_path": "a.py", "reason": "blocked"})
    elif mutation == "support":
        item = replace(item, support_type=SupportType.HEURISTIC)
    results = ranked(req, [item])
    policy = EvidenceSelectionPolicy(
        100,
        2,
        allowed_support_types=(SupportType.SOURCE_EXACT,),
    )

    context = EvidenceSelector().select(repository, req, results, policy)

    assert context.status is EvidenceContextStatus.INSUFFICIENT
    assert context.rejected[0].reason_code == reason


def test_budget_never_truncates_a_block_and_reports_oversized_requirement(tmp_path: Path) -> None:
    repository = repository_with_files(tmp_path, {"a.py": "x" * 80 + "\n"})
    req = request()
    results = ranked(req, [candidate(repository, "a.py", name="large", rank=1)])

    context = EvidenceSelector().select(
        repository, req, results, EvidenceSelectionPolicy(token_budget=30, max_evidence=2)
    )

    assert context.status is EvidenceContextStatus.INSUFFICIENT
    assert not context.selected
    assert context.rejected[0].reason_code == "block_exceeds_token_budget"
    assert context.truncation_reason == "whole_block_budget_limit"


def test_selection_prefers_source_diversity_and_is_input_order_invariant(tmp_path: Path) -> None:
    repository = repository_with_files(
        tmp_path,
        {
            "a.py": "first = 1\nsecond = 2\n",
            "b.py": "third = 3\n",
        },
    )
    req = request(limit=3)
    results = ranked(
        req,
        [
            candidate(repository, "a.py", name="first", rank=1, start_line=1),
            candidate(repository, "a.py", name="second", rank=2, start_line=2),
            candidate(repository, "b.py", name="third", rank=3),
        ],
    )
    policy = EvidenceSelectionPolicy(token_budget=200, max_evidence=2)

    first = EvidenceSelector().select(repository, req, results, policy)
    second = EvidenceSelector().select(repository, req, list(reversed(results)), policy)

    assert [item.file_path for item in first.selected] == ["a.py", "b.py"]
    assert first == second
    assert first.status is EvidenceContextStatus.LIMITED


def test_partial_budget_and_multi_step_undercoverage_remain_insufficient(tmp_path: Path) -> None:
    repository = repository_with_files(
        tmp_path, {"a.py": "a = 1\n", "b.py": "b = " + "x" * 80 + "\n"}
    )
    req = request(QuestionType.FLOW_TRACING)
    results = ranked(
        req,
        [
            candidate(repository, "a.py", name="a", rank=1, retriever=RetrieverName.GRAPH),
            candidate(repository, "b.py", name="b", rank=2, retriever=RetrieverName.GRAPH),
        ],
    )

    context = EvidenceSelector().select(
        repository, req, results, EvidenceSelectionPolicy(token_budget=50, max_evidence=3)
    )

    assert len(context.selected) == 1
    assert context.status is EvidenceContextStatus.INSUFFICIENT
    assert context.missing_requirements == ("required_evidence_count:2",)
    assert context.truncation_reason == "whole_block_budget_limit"


@pytest.mark.parametrize(
    "policy",
    [
        EvidenceSelectionPolicy,
    ],
)
def test_policy_rejects_invalid_limits(policy) -> None:
    with pytest.raises(ValueError):
        policy(token_budget=0, max_evidence=1)
    with pytest.raises(ValueError):
        policy(token_budget=1, max_evidence=0)
    with pytest.raises(ValueError):
        policy(token_budget=1, max_evidence=1, chars_per_token=0)


def test_agent_workflow_persists_only_selected_validated_context(tmp_path: Path) -> None:
    repository = repository_with_files(tmp_path, {"src/a.py": "def calculate():\n    return 1\n"})
    item = candidate(repository, "src/a.py", name="calculate", rank=1, end_line=2)
    repository.chunks.append(item.chunk)
    store = MemoryEvidenceStore()
    workflow = AgentWorkflowService(RetrievalService(), EvidenceService(store))

    result = workflow.answer(repository, "calculate")

    assert result.evidence_sufficient is True
    assert len(result.citations) == 1
    assert result.citations[0].evidence_id.startswith("evidence_")
    assert list(store.evidence) == [result.citations[0].evidence_id]
