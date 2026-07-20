from __future__ import annotations

from dataclasses import dataclass

from app.schemas.api import CitationDTO
from app.services.index_models import ChunkRecord, RepositoryState
from app.services.retrieval.contracts import QueryClassification, RetrievalCandidate, RetrievalRequest
from app.services.retrieval.query_classifier import QueryClassifier
from app.services.retrieval.ranking import (
    RankedCandidate,
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
from app.services.retrieval.vector_search_service import (
    LocalVectorSearchService,
    VectorSearchProvider,
)


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
        vector_search: VectorSearchProvider | None = None,
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
        classification: QueryClassification | None = None,
    ) -> tuple[RetrievalRequest, list[RetrievalCandidate]]:
        classification = classification or self.classifier.classify(query)
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
        _, ranked_candidates = self.ranked_search(repository, query, limit)
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
            for ranked in ranked_candidates
        ]

    def ranked_search(
        self,
        repository: RepositoryState,
        query: str,
        limit: int,
        classification: QueryClassification | None = None,
    ) -> tuple[RetrievalRequest, list[RankedCandidate]]:
        """Return the owned request and inspectable ranked candidates."""
        request, candidates = self.retrieve_candidates(repository, query, limit, classification)
        return request, self.ranker.rank(request, candidates)

    def generate_grounded_answer(self, question_type: str, message: str, citations: list[CitationDTO]) -> str:
        first = citations[0]
        if question_type == "flow_tracing":
            return (
                f"The primary supporting evidence is {first.file_path}:{first.start_line}-{first.end_line}. "
                "The system finds related endpoints, symbols, and files in the index, then ranks evidence by its match to the question. "
                "Treat this flow as grounded only within the returned citations."
            )
        if question_type == "debugging":
            return (
                f"Start debugging at {first.file_path}:{first.start_line}-{first.end_line}, then inspect the remaining citations. "
                "For configuration issues, the system uses only indexed configuration files and never reads a real .env file."
            )
        if question_type == "architecture_overview":
            return (
                "The architecture summary is derived from source files, README/docs, and parser metadata. "
                f"The strongest current evidence is {first.file_path}:{first.start_line}-{first.end_line}."
            )
        return (
            f"The system found evidence related to the question '{message}'. "
            f"The main conclusion is anchored to {first.file_path}:{first.start_line}-{first.end_line} and the accompanying citations."
        )
