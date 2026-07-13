from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from math import ceil

from app.services.index_models import FileRecord, RepositoryState
from app.services.retrieval.contracts import QuestionType, RetrievalRequest, SupportType
from app.services.retrieval.ranking import RankedCandidate, SUPPORT_ORDER
from app.services.text_utils import content_hash, read_text


class EvidenceContextStatus(str, Enum):
    READY = "ready"
    LIMITED = "limited"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class EvidenceSelectionPolicy:
    token_budget: int
    max_evidence: int
    chars_per_token: int = 4
    per_block_overhead_tokens: int = 24
    allowed_support_types: tuple[SupportType, ...] = tuple(SupportType)

    def __post_init__(self) -> None:
        if self.token_budget <= 0 or self.max_evidence <= 0:
            raise ValueError("evidence token budget and limit must be positive")
        if self.chars_per_token <= 0 or self.per_block_overhead_tokens < 0:
            raise ValueError("evidence token estimator values are invalid")
        if not self.allowed_support_types or len(set(self.allowed_support_types)) != len(
            self.allowed_support_types
        ):
            raise ValueError("allowed evidence support types must be non-empty and unique")
        if any(not isinstance(item, SupportType) for item in self.allowed_support_types):
            raise ValueError("allowed evidence support types must be controlled")


@dataclass(frozen=True)
class ValidatedEvidenceBlock:
    evidence_id: str
    candidate_ids: tuple[str, ...]
    repository_id: str
    index_version_id: str
    ranking_config_id: str
    source_key: str
    entity_key: str
    file_path: str
    start_line: int
    end_line: int
    symbol_name: str | None
    source_type: str
    source_sha256: str
    chunk_sha256: str
    support_type: SupportType
    retrievers: tuple[str, ...]
    reason_codes: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    content: str
    token_estimate: int
    normalized_score: float


@dataclass(frozen=True)
class RejectedEvidence:
    candidate_ids: tuple[str, ...]
    reason_code: str


@dataclass(frozen=True)
class OmissionSummary:
    reason_code: str
    count: int


@dataclass(frozen=True)
class EvidenceContext:
    repository_id: str
    index_version_id: str
    ranking_config_id: str | None
    selected: tuple[ValidatedEvidenceBlock, ...]
    rejected: tuple[RejectedEvidence, ...]
    omitted_summary: tuple[OmissionSummary, ...]
    token_budget: int
    used_tokens: int
    status: EvidenceContextStatus
    truncation_reason: str | None
    missing_requirements: tuple[str, ...]


class EvidenceSelector:
    """Validate and select immutable whole evidence spans deterministically."""

    def select(
        self,
        repository: RepositoryState,
        request: RetrievalRequest,
        ranked_candidates: list[RankedCandidate],
        policy: EvidenceSelectionPolicy,
    ) -> EvidenceContext:
        if request.repository_id != repository.id:
            raise ValueError("retrieval request repository ownership mismatch")
        for ranked in ranked_candidates:
            ranked.candidate.validate_ownership(request)

        ranking_ids = {ranked.ranking_config_id for ranked in ranked_candidates}
        if len(ranking_ids) > 1:
            raise ValueError("ranked candidates use multiple ranking configurations")
        ranking_config_id = next(iter(ranking_ids), None)
        current_index_id = f"idx_compat_{max(repository.current_index_version, 0)}"
        if request.index_version_id != current_index_id:
            rejected = tuple(
                RejectedEvidence(ranked.candidate_ids, "stale_index_version")
                for ranked in self._stable_order(request, ranked_candidates)
            )
            return self._context(
                request,
                ranking_config_id,
                (),
                rejected,
                policy,
                required_count=self._required_count(request),
            )

        files = {item.path: item for item in repository.files}
        blocked_paths = self._blocked_paths(repository)
        eligible: list[ValidatedEvidenceBlock] = []
        rejected: list[RejectedEvidence] = []
        for ranked in self._stable_order(request, ranked_candidates):
            block, reason = self._validate_candidate(
                repository,
                request,
                ranked,
                policy,
                files,
                blocked_paths,
            )
            if block is None:
                rejected.append(RejectedEvidence(ranked.candidate_ids, reason or "invalid_candidate"))
            else:
                eligible.append(block)

        selected: list[ValidatedEvidenceBlock] = []
        deferred: list[ValidatedEvidenceBlock] = []
        seen_sources: set[str] = set()
        for block in eligible:
            if block.file_path in seen_sources:
                deferred.append(block)
            else:
                selected.append(block)
                seen_sources.add(block.file_path)
        ordered = selected + deferred
        selected = []
        used_tokens = 0
        for block in ordered:
            if len(selected) >= policy.max_evidence:
                rejected.append(RejectedEvidence(block.candidate_ids, "evidence_limit_reached"))
                continue
            if block.token_estimate > policy.token_budget:
                rejected.append(RejectedEvidence(block.candidate_ids, "block_exceeds_token_budget"))
                continue
            if used_tokens + block.token_estimate > policy.token_budget:
                rejected.append(RejectedEvidence(block.candidate_ids, "token_budget_exceeded"))
                continue
            selected.append(block)
            used_tokens += block.token_estimate

        return self._context(
            request,
            ranking_config_id,
            tuple(selected),
            tuple(sorted(rejected, key=lambda item: (item.reason_code, item.candidate_ids))),
            policy,
            required_count=self._required_count(request),
        )

    def _validate_candidate(
        self,
        repository: RepositoryState,
        request: RetrievalRequest,
        ranked: RankedCandidate,
        policy: EvidenceSelectionPolicy,
        files: dict[str, FileRecord],
        blocked_paths: set[str],
    ) -> tuple[ValidatedEvidenceBlock | None, str | None]:
        candidate = ranked.candidate
        chunk = candidate.chunk
        if ranked.support_type not in policy.allowed_support_types:
            return None, "unsupported_support_type"
        if chunk.file_path in blocked_paths:
            return None, "blocked_source"
        file_record = files.get(chunk.file_path)
        if file_record is None or candidate.source_key != f"file:v1:{chunk.file_path}":
            return None, "source_not_in_current_index"
        if not file_record.absolute_path.is_file():
            return None, "source_missing"
        try:
            source_bytes = file_record.absolute_path.read_bytes()
        except OSError:
            return None, "source_missing"
        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        if source_sha256 != file_record.content_hash:
            return None, "source_hash_changed"
        try:
            lines = read_text(file_record.absolute_path).splitlines()
        except OSError:
            return None, "source_missing"
        if chunk.start_line < 1 or chunk.end_line < chunk.start_line or chunk.end_line > len(lines):
            return None, "range_invalid"
        expected_chunk_hash = content_hash(
            f"{chunk.file_path}:{chunk.start_line}:{chunk.end_line}:{chunk.content.strip()}"
        )
        if len(chunk.content_hash) != 64 or chunk.content_hash != expected_chunk_hash:
            return None, "chunk_hash_changed"

        token_estimate = policy.per_block_overhead_tokens + ceil(
            len(chunk.content) / policy.chars_per_token
        )
        evidence_id = self._evidence_id(
            repository.id,
            request.index_version_id,
            candidate.source_key,
            source_sha256,
            chunk.content_hash,
            chunk.start_line,
            chunk.end_line,
        )
        return (
            ValidatedEvidenceBlock(
                evidence_id=evidence_id,
                candidate_ids=ranked.candidate_ids,
                repository_id=repository.id,
                index_version_id=request.index_version_id,
                ranking_config_id=ranked.ranking_config_id,
                source_key=candidate.source_key,
                entity_key=candidate.entity_key,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                symbol_name=chunk.symbol_name,
                source_type=(
                    "document" if chunk.chunk_type in {"doc_section", "config_section"} else "code"
                ),
                source_sha256=source_sha256,
                chunk_sha256=chunk.content_hash,
                support_type=ranked.support_type,
                retrievers=tuple(item.value for item in ranked.retrievers),
                reason_codes=ranked.reason_codes,
                provenance_refs=ranked.provenance_refs,
                content=chunk.content,
                token_estimate=token_estimate,
                normalized_score=ranked.normalized_score,
            ),
            None,
        )

    def _stable_order(
        self, request: RetrievalRequest, ranked_candidates: list[RankedCandidate]
    ) -> list[RankedCandidate]:
        question_type = request.classification.question_type
        return sorted(
            ranked_candidates,
            key=lambda item: (
                self._coverage_priority(question_type, item),
                0 if "exact_named_target" in item.reason_codes else 1,
                SUPPORT_ORDER[item.support_type],
                -item.fused_score,
                item.best_rank,
                item.candidate.entity_key,
                item.candidate.candidate_id,
            ),
        )

    @staticmethod
    def _coverage_priority(question_type: QuestionType, ranked: RankedCandidate) -> int:
        retrievers = {item.value for item in ranked.retrievers}
        chunk_type = ranked.candidate.chunk.chunk_type
        if question_type == QuestionType.API_QUESTION:
            return 0 if "endpoint" in retrievers else 1
        if question_type in {QuestionType.FLOW_TRACING, QuestionType.IMPACT_ANALYSIS}:
            return 0 if "graph" in retrievers else 1
        if question_type in {QuestionType.ARCHITECTURE_OVERVIEW, QuestionType.ONBOARDING}:
            return 0 if chunk_type in {"doc_section", "file_summary"} else 1
        return 0

    @staticmethod
    def _required_count(request: RetrievalRequest) -> int:
        if request.classification.question_type in {
            QuestionType.FLOW_TRACING,
            QuestionType.API_QUESTION,
            QuestionType.IMPACT_ANALYSIS,
        }:
            return 2
        return 1

    @staticmethod
    def _blocked_paths(repository: RepositoryState) -> set[str]:
        paths: set[str] = set()
        records = [
            *repository.skipped_file_records,
            *getattr(repository, "security_warning_records", []),
        ]
        for record in records:
            value = record.get("file_path") or record.get("path")
            if isinstance(value, str) and value:
                paths.add(value)
        return paths

    @staticmethod
    def _evidence_id(
        repository_id: str,
        index_version_id: str,
        source_key: str,
        source_sha256: str,
        chunk_sha256: str,
        start_line: int,
        end_line: int,
    ) -> str:
        payload = json.dumps(
            [
                repository_id,
                index_version_id,
                source_key,
                source_sha256,
                chunk_sha256,
                start_line,
                end_line,
            ],
            ensure_ascii=True,
            separators=(",", ":"),
        )
        return f"evidence_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"

    @staticmethod
    def _context(
        request: RetrievalRequest,
        ranking_config_id: str | None,
        selected: tuple[ValidatedEvidenceBlock, ...],
        rejected: tuple[RejectedEvidence, ...],
        policy: EvidenceSelectionPolicy,
        required_count: int,
    ) -> EvidenceContext:
        missing = () if len(selected) >= required_count else (f"required_evidence_count:{required_count}",)
        if missing:
            status = EvidenceContextStatus.INSUFFICIENT
        elif rejected:
            status = EvidenceContextStatus.LIMITED
        else:
            status = EvidenceContextStatus.READY
        counts: dict[str, int] = {}
        for item in rejected:
            counts[item.reason_code] = counts.get(item.reason_code, 0) + len(item.candidate_ids)
        omitted = tuple(OmissionSummary(reason, counts[reason]) for reason in sorted(counts))
        budget_reasons = {"block_exceeds_token_budget", "token_budget_exceeded"}
        truncation_reason = "whole_block_budget_limit" if any(
            item.reason_code in budget_reasons for item in rejected
        ) else None
        return EvidenceContext(
            repository_id=request.repository_id,
            index_version_id=request.index_version_id,
            ranking_config_id=ranking_config_id,
            selected=selected,
            rejected=rejected,
            omitted_summary=omitted,
            token_budget=policy.token_budget,
            used_tokens=sum(item.token_estimate for item in selected),
            status=status,
            truncation_reason=truncation_reason,
            missing_requirements=missing,
        )
