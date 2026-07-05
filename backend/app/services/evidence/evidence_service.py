from __future__ import annotations

from uuid import uuid4

from app.core.errors import DomainError
from app.schemas.api import CitationDTO, EvidenceDTO, EvidenceValidationItemDTO, EvidenceValidationResponse
from app.services.index_models import ChunkRecord, RepositoryState
from app.services.repositories.repository_store import RepositoryStore
from app.services.text_utils import preview, read_text


class EvidenceService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store
        self.cache: dict[str, EvidenceDTO] = {}

    def get_evidence(self, repository_id: str, evidence_id: str) -> EvidenceDTO:
        evidence = self.cache.get(evidence_id)
        if evidence is None:
            evidence = self.store.get_evidence(evidence_id)
        if evidence is None or evidence.repository_id != repository_id:
            raise DomainError("EVIDENCE_NOT_FOUND", "Evidence not found.", 404, {"evidence_id": evidence_id})
        self.cache[evidence.evidence_id] = evidence
        return evidence

    def clear_repository(self, repository_id: str) -> None:
        self.cache = {
            evidence_id: evidence
            for evidence_id, evidence in self.cache.items()
            if evidence.repository_id != repository_id
        }

    def validate_evidence(self, repository: RepositoryState, evidence_ids: list[str]) -> EvidenceValidationResponse:
        return EvidenceValidationResponse(
            items=[self._validate_evidence_id(repository, evidence_id) for evidence_id in evidence_ids]
        )

    def chunk_to_citation(self, repository: RepositoryState, chunk: ChunkRecord, retrieval_source: str) -> CitationDTO:
        evidence_id = f"ev_{uuid4().hex[:10]}"
        evidence = EvidenceDTO(
            evidence_id=evidence_id,
            repository_id=repository.id,
            source_type="code" if chunk.chunk_type not in {"doc_section", "config_section"} else "document",
            file_path=chunk.file_path,
            symbol_name=chunk.symbol_name,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            index_version=repository.current_index_version,
            content_preview=preview(chunk.content),
            relevance_reason=f"Matched by {retrieval_source} for {chunk.chunk_type}",
            confidence_score=round(max(0.5, chunk.score), 2),
            retrieval_source=retrieval_source,
            is_stale=False,
            metadata={"chunk_type": chunk.chunk_type},
        )
        self.cache[evidence_id] = evidence
        self.store.save_evidence(evidence)
        return CitationDTO(
            evidence_id=evidence_id,
            file_path=chunk.file_path,
            symbol_name=chunk.symbol_name,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            index_version=repository.current_index_version,
            is_stale=False,
        )

    def _validate_evidence_id(self, repository: RepositoryState, evidence_id: str) -> EvidenceValidationItemDTO:
        try:
            evidence = self.get_evidence(repository.id, evidence_id)
        except DomainError:
            return EvidenceValidationItemDTO(evidence_id=evidence_id, is_valid=False, reason="evidence_not_found")

        if evidence.index_version != repository.current_index_version or evidence.is_stale:
            return EvidenceValidationItemDTO(
                evidence_id=evidence_id,
                is_valid=False,
                is_stale=True,
                reason="stale_index_version",
            )

        file_record = next((item for item in repository.files if item.path == evidence.file_path), None)
        if file_record is None:
            return EvidenceValidationItemDTO(evidence_id=evidence_id, is_valid=False, reason="file_not_in_current_index")

        try:
            line_count = len(read_text(file_record.absolute_path).splitlines())
        except OSError:
            return EvidenceValidationItemDTO(evidence_id=evidence_id, is_valid=False, reason="source_file_missing")

        if evidence.start_line < 1 or evidence.end_line < evidence.start_line or evidence.end_line > line_count:
            return EvidenceValidationItemDTO(evidence_id=evidence_id, is_valid=False, reason="line_range_out_of_bounds")

        return EvidenceValidationItemDTO(evidence_id=evidence_id, is_valid=True, is_stale=False, reason=None)
