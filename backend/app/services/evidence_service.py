from __future__ import annotations

from uuid import uuid4

from app.core.errors import DomainError
from app.schemas.api import CitationDTO, EvidenceDTO
from app.services.index_models import ChunkRecord, RepositoryState
from app.services.repository_store import RepositoryStore
from app.services.text_utils import preview


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
            content_preview=preview(chunk.content),
            relevance_reason=f"Matched by {retrieval_source} for {chunk.chunk_type}",
            confidence_score=round(max(0.5, chunk.score), 2),
            retrieval_source=retrieval_source,
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
        )
