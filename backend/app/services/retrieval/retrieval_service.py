from __future__ import annotations

from dataclasses import dataclass

from app.schemas.api import CitationDTO
from app.services.index_models import ChunkRecord, RepositoryState
from app.services.retrieval.contracts import RetrievalCandidate, RetrievalRequest
from app.services.retrieval.query_classifier import QueryClassifier
from app.services.retrieval.ranking import (
    RankingConfiguration,
    ReciprocalRankRanker,
    default_ranking_configuration,
)
from app.services.retrieval.retrievers import (
    EndpointRetriever,
    ExactRetriever,
    GraphRetriever,
    LexicalRetriever,
    MetadataRetriever,
    RetrievalScorer,
    SemanticRetriever,
    SymbolRetriever,
)
from app.services.retrieval.vector_search_service import LocalVectorSearchService


@dataclass(frozen=True)
class HybridSearchMatch:
    chunk: ChunkRecord
    score: float
    result_type: str
    retrieval_source: str
    title: str
    matched_terms: list[str]


class RetrievalService:
    """Compatibility facade over typed deterministic retrievers.

    RET-002 fuses incomparable retriever scores by typed rank only. The public
    interface remains stable while ranking policy becomes inspectable/versioned.
    """

    def __init__(
        self,
        vector_search: LocalVectorSearchService | None = None,
        classifier: QueryClassifier | None = None,
        ranking_configuration: RankingConfiguration | None = None,
    ) -> None:
        self.vector_search = vector_search or LocalVectorSearchService()
        self.classifier = classifier or QueryClassifier()
        self.ranking_configuration = ranking_configuration or default_ranking_configuration()
        self.ranker = ReciprocalRankRanker(self.ranking_configuration)
        scorer = RetrievalScorer()
        self.lexical_retriever = LexicalRetriever(scorer)
        self.semantic_retriever = SemanticRetriever(scorer, self.vector_search)
        self.symbol_retriever = SymbolRetriever(scorer)
        self.endpoint_retriever = EndpointRetriever(scorer)
        self.metadata_retriever = MetadataRetriever(scorer)
        self.graph_retriever = GraphRetriever(scorer)
        self.exact_retriever = ExactRetriever(
            scorer,
            (self.symbol_retriever, self.endpoint_retriever, self.metadata_retriever),
        )
        self.retrievers = (
            self.lexical_retriever,
            self.semantic_retriever,
            self.symbol_retriever,
            self.endpoint_retriever,
            self.metadata_retriever,
            self.graph_retriever,
            self.exact_retriever,
        )

    def classify_question(self, question: str) -> str:
        return self.classifier.classify(question).compatibility_label

    def search_chunks(self, repository: RepositoryState, query: str, limit: int) -> list[ChunkRecord]:
        return [
            ChunkRecord(**{**match.chunk.__dict__, "score": match.score})
            for match in self.hybrid_search(repository, query, limit)
        ]

    def retrieve_candidates(
        self,
        repository: RepositoryState,
        query: str,
        limit: int,
    ) -> tuple[RetrievalRequest, list[RetrievalCandidate]]:
        classification = self.classifier.classify(query)
        request = RetrievalRequest.for_repository(repository, query, limit, classification)
        if not RetrievalScorer().query_terms(query):
            return request, []

        candidates = [
            candidate
            for retriever in self.retrievers
            for candidate in retriever.retrieve(request, repository)
        ]
        candidates.extend(self.graph_retriever.related_candidates(request, repository, candidates))
        return request, candidates

    def hybrid_search(self, repository: RepositoryState, query: str, limit: int) -> list[HybridSearchMatch]:
        request, candidates = self.retrieve_candidates(repository, query, limit)
        return [
            HybridSearchMatch(
                chunk=ChunkRecord(
                    **{
                        **ranked.candidate.chunk.__dict__,
                        "score": round(ranked.normalized_score, 4),
                    }
                ),
                score=round(ranked.normalized_score, 4),
                result_type=ranked.candidate.result_type,
                retrieval_source=ranked.candidate.compatibility_source,
                title=ranked.candidate.title,
                matched_terms=list(ranked.matched_terms),
            )
            for ranked in self.ranker.rank(request, candidates)
        ]

    def generate_grounded_answer(self, question_type: str, message: str, citations: list[CitationDTO]) -> str:
        first = citations[0]
        if question_type == "flow_tracing":
            return (
                f"Luong xu ly co evidence chinh tai {first.file_path}:{first.start_line}-{first.end_line}. "
                "He thong tim cac endpoint, symbol va file lien quan trong index, sau do sap xep evidence theo do khop voi cau hoi. "
                "Cac buoc chi nen xem la grounded trong pham vi citation duoc tra ve."
            )
        if question_type == "debugging":
            return (
                f"Bat dau debug tu {first.file_path}:{first.start_line}-{first.end_line}, sau do kiem tra cac citation con lai. "
                "Neu loi lien quan config, he thong chi dung file config duoc index va khong doc .env that."
            )
        if question_type == "architecture_overview":
            return (
                "Kien truc duoc tom tat tu file source, README/docs va metadata parser. "
                f"Evidence manh nhat hien tai la {first.file_path}:{first.start_line}-{first.end_line}."
            )
        return (
            f"He thong tim thay evidence lien quan cho cau hoi '{message}'. "
            f"Ket luan chinh duoc neo vao {first.file_path}:{first.start_line}-{first.end_line} va cac citation kem theo."
        )
