from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib

from app.schemas.api import CitationDTO
from app.services.evidence.evidence_service import EvidenceService
from app.services.index_models import RepositoryState


class ClaimSupportLevel(str, Enum):
    DIRECT = "direct"
    MULTI_HOP = "multi_hop"
    INFERRED = "inferred"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class AnswerClaim:
    claim_id: str
    text: str
    support_level: ClaimSupportLevel
    citation_ids: tuple[str, ...]

    @classmethod
    def from_answer(
        cls, answer: str, citation_ids: tuple[str, ...], support_level: ClaimSupportLevel
    ) -> AnswerClaim:
        digest = hashlib.sha256((answer + "|" + "|".join(citation_ids)).encode("utf-8")).hexdigest()[:24]
        return cls(f"claim_{digest}", answer.strip(), support_level, citation_ids)


@dataclass(frozen=True)
class ClaimValidationItem:
    claim_id: str
    valid: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CitationValidationResult:
    valid: bool
    items: tuple[ClaimValidationItem, ...]
    validated_citation_ids: tuple[str, ...]


class ClaimCitationValidator:
    def __init__(self, evidence: EvidenceService) -> None:
        self.evidence = evidence

    def validate(
        self,
        repository: RepositoryState,
        claims: tuple[AnswerClaim, ...],
        citations: list[CitationDTO],
        selected_evidence_ids: tuple[str, ...],
    ) -> CitationValidationResult:
        citation_by_id = {citation.evidence_id: citation for citation in citations}
        selected = set(selected_evidence_ids)
        items: list[ClaimValidationItem] = []
        validated: set[str] = set()
        for claim in claims:
            reasons: list[str] = []
            if not claim.claim_id.startswith("claim_") or not claim.text:
                reasons.append("claim_invalid")
            if len(claim.citation_ids) != len(set(claim.citation_ids)):
                reasons.append("duplicate_claim_citation")
            if claim.support_level is ClaimSupportLevel.INSUFFICIENT and claim.citation_ids:
                reasons.append("insufficient_claim_has_citations")
            if claim.support_level is not ClaimSupportLevel.INSUFFICIENT and not claim.citation_ids:
                reasons.append("claim_missing_citation")
            for evidence_id in claim.citation_ids:
                if evidence_id not in selected:
                    reasons.append("citation_not_selected")
                    continue
                citation = citation_by_id.get(evidence_id)
                if citation is None:
                    reasons.append("citation_missing_from_response")
                    continue
                validation = self.evidence.validate_evidence(repository, [evidence_id]).items[0]
                if not validation.is_valid:
                    reasons.append(validation.reason or "citation_invalid")
                    continue
                evidence = self.evidence.get_evidence(repository.id, evidence_id)
                if (
                    citation.index_version != repository.current_index_version
                    or citation.file_path != evidence.file_path
                    or citation.start_line != evidence.start_line
                    or citation.end_line != evidence.end_line
                ):
                    reasons.append("citation_scope_mismatch")
                    continue
                validated.add(evidence_id)
            items.append(
                ClaimValidationItem(claim.claim_id, not reasons, tuple(dict.fromkeys(reasons)))
            )
        return CitationValidationResult(
            valid=bool(items) and all(item.valid for item in items),
            items=tuple(items),
            validated_citation_ids=tuple(sorted(validated)),
        )
