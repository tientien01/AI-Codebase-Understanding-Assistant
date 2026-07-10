from __future__ import annotations

from pathlib import Path

from app.schemas.api import SearchResponse, SearchResultDTO
from app.services.evidence.evidence_service import EvidenceService
from app.services.repositories.repository_service import RepositoryService
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.text_utils import preview


class SearchService:
    def __init__(
        self,
        repositories: RepositoryService,
        retrieval: RetrievalService,
        evidence: EvidenceService,
    ) -> None:
        self.repositories = repositories
        self.retrieval = retrieval
        self.evidence = evidence

    def search(self, repository_id: str, query: str) -> SearchResponse:
        repository = self.repositories.get_indexed_repository(repository_id)
        matches = self.retrieval.hybrid_search(repository, query, limit=10)
        results = []
        for match in matches:
            chunk = match.chunk
            citation = self.evidence.chunk_to_citation(repository, chunk, match.retrieval_source)
            results.append(
                SearchResultDTO(
                    evidence_id=citation.evidence_id,
                    file_path=chunk.file_path,
                    title=match.title or chunk.symbol_name or Path(chunk.file_path).name,
                    preview=preview(chunk.content),
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    score=round(match.score, 2),
                    result_type=match.result_type,
                    retrieval_source=match.retrieval_source,
                    matched_terms=match.matched_terms,
                    index_version=citation.index_version,
                    is_stale=citation.is_stale,
                )
            )
        return SearchResponse(results=results)
