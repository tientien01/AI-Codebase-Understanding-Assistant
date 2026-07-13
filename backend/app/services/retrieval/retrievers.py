from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from math import log
from pathlib import Path
import re
from typing import Protocol

from app.services.index_models import ChunkRecord, EndpointRecord, FileRecord, RepositoryState, SymbolRecord
from app.services.retrieval.contracts import (
    RetrievalCandidate,
    RetrievalRequest,
    RetrieverName,
    SupportType,
    candidate_id,
)
from app.services.retrieval.vector_search_service import LocalVectorSearchService


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "what", "where", "when", "how", "can", "you",
    "toi", "cua", "cho", "nao", "nhu", "the", "hoat", "dong",
}

QUESTION_TYPE_CHUNK_BOOSTS = {
    "api_question": {"endpoint": 2.0, "function": 0.5, "method": 0.5},
    "flow_tracing": {"endpoint": 1.0, "function": 1.0, "method": 1.0},
    "architecture_overview": {"doc_section": 1.5, "file_summary": 1.0},
    "debugging": {"function": 0.8, "method": 0.8, "file_summary": 0.4},
}


@dataclass(frozen=True)
class CandidateSeed:
    chunk: ChunkRecord
    raw_score: float
    result_type: str
    title: str
    matched_terms: tuple[str, ...]
    reason_codes: tuple[str, ...]
    compatibility_source: str
    support_type: SupportType
    provenance_refs: tuple[str, ...] = ()


class Retriever(Protocol):
    name: RetrieverName
    version: str

    def retrieve(self, request: RetrievalRequest, repository: RepositoryState) -> list[RetrievalCandidate]: ...


class RetrievalScorer:
    """Shared deterministic scoring primitives; it owns no repository or provider state."""

    def query_terms(self, query: str) -> list[str]:
        raw_terms = re.findall(r"[\w/.-]+", query.lower())
        deduped: list[str] = []
        seen: set[str] = set()
        for term in raw_terms:
            if len(term) <= 1 or term in STOPWORDS or term in seen:
                continue
            seen.add(term)
            deduped.append(term)
        return deduped

    def score_chunks(
        self,
        repository: RepositoryState,
        terms: list[str],
        question_type: str,
        query: str,
    ) -> list[CandidateSeed]:
        idf = self._idf_by_term(repository.chunks, terms)
        avg_len = sum(len(self.tokens(self.chunk_haystack(chunk))) for chunk in repository.chunks) / max(len(repository.chunks), 1)
        seeds: list[CandidateSeed] = []
        for chunk in repository.chunks:
            haystack = self.chunk_haystack(chunk)
            score = self._bm25_score(terms, haystack, idf, avg_len)
            score += self.lexical_score(terms, haystack) * 0.65
            score += self.fuzzy_score(terms, haystack) * 0.8
            score += QUESTION_TYPE_CHUNK_BOOSTS.get(question_type, {}).get(chunk.chunk_type, 0.0)
            normalized_query = query.lower()
            reasons = ["lexical_chunk_match"]
            if chunk.symbol_name and chunk.symbol_name.lower() in normalized_query:
                score += 3
                reasons.append("exact_symbol_in_query")
            if chunk.file_path.lower() in normalized_query:
                score += 3
                reasons.append("exact_file_in_query")
            if chunk.chunk_type == "endpoint" and any(term in haystack for term in terms):
                score += 1
                reasons.append("endpoint_term_match")
            if "login" in normalized_query and ("login" in haystack or "auth" in haystack):
                score += 3
                reasons.append("login_auth_compatibility_boost")
            if score > 0:
                seeds.append(
                    CandidateSeed(
                        chunk=chunk,
                        raw_score=score,
                        result_type="file" if chunk.chunk_type == "file_summary" else chunk.chunk_type,
                        title=chunk.symbol_name or Path(chunk.file_path).name,
                        matched_terms=tuple(self.matched_terms(terms, haystack)),
                        reason_codes=tuple(reasons),
                        compatibility_source="chunk",
                        support_type=SupportType.SOURCE_EXACT,
                    )
                )
        return seeds

    def score_text(self, terms: list[str], haystack: str, query: str) -> tuple[float, list[str]]:
        normalized = haystack.lower()
        score = self.lexical_score(terms, normalized) + self.fuzzy_score(terms, normalized)
        if query.lower().strip() and query.lower().strip() in normalized:
            score += 2.0
        return score, self.matched_terms(terms, normalized)

    def lexical_score(self, terms: list[str], haystack: str) -> float:
        if not terms:
            return 0.0
        score = 0.0
        haystack_tokens = set(re.findall(r"[\w/.-]+", haystack))
        for term in terms:
            if term in haystack_tokens:
                score += 2.0
            elif term in haystack:
                score += 0.75
        return score

    def fuzzy_score(self, terms: list[str], haystack: str) -> float:
        tokens = self.tokens(haystack)
        if not tokens:
            return 0.0
        score = 0.0
        for term in terms:
            best = max(SequenceMatcher(None, term, token).ratio() for token in tokens)
            if best >= 0.88:
                score += 1.2
            elif best >= 0.76:
                score += 0.55
        return score

    def tokens(self, text: str) -> list[str]:
        return re.findall(r"[\w/.-]+", text.lower())

    def matched_terms(self, terms: list[str], haystack: str) -> list[str]:
        tokens = set(self.tokens(haystack))
        return [term for term in terms if term in tokens or term in haystack]

    def chunk_haystack(self, chunk: ChunkRecord) -> str:
        return f"{chunk.file_path} {chunk.symbol_name or ''} {chunk.chunk_type} {chunk.content}".lower()

    def symbol_haystack(self, symbol: SymbolRecord) -> str:
        return f"{symbol.name} {symbol.symbol_type} {symbol.signature} {symbol.file_path}".lower()

    def endpoint_haystack(self, endpoint: EndpointRecord) -> str:
        metadata = " ".join(f"{key} {value}" for key, value in endpoint.metadata.items())
        return f"{endpoint.method} {endpoint.path} {endpoint.handler} {endpoint.file_path} {metadata}".lower()

    def file_haystack(self, file_record: FileRecord) -> str:
        return f"{file_record.path} {Path(file_record.path).name} {file_record.language} {file_record.file_type}".lower()

    def graph_node_haystack(self, node) -> str:
        return " ".join(
            (node.label, node.type, node.file_path or "", node.role or "", node.summary or "", node.layer or "", " ".join(node.tags))
        ).lower()

    def chunk_for_symbol(self, repository: RepositoryState, symbol: SymbolRecord) -> ChunkRecord | None:
        return next(
            (
                chunk for chunk in repository.chunks
                if chunk.file_path == symbol.file_path
                and (chunk.symbol_name == symbol.name or (chunk.start_line == symbol.start_line and chunk.end_line == symbol.end_line))
            ),
            None,
        )

    def chunk_for_endpoint(self, repository: RepositoryState, endpoint: EndpointRecord) -> ChunkRecord | None:
        return next(
            (
                chunk for chunk in repository.chunks
                if chunk.file_path == endpoint.file_path and chunk.chunk_type == "endpoint"
                and (chunk.symbol_name == endpoint.handler or endpoint.path in chunk.content)
            ),
            None,
        )

    def file_summary_chunk(self, repository: RepositoryState, file_path: str) -> ChunkRecord | None:
        return next(
            (chunk for chunk in repository.chunks if chunk.file_path == file_path and chunk.chunk_type == "file_summary"),
            None,
        ) or next((chunk for chunk in repository.chunks if chunk.file_path == file_path), None)

    def chunk_for_graph_node(self, repository: RepositoryState, node) -> ChunkRecord | None:
        if not node.file_path:
            return None
        if node.start_line is not None and node.end_line is not None:
            by_range = next(
                (
                    chunk for chunk in repository.chunks
                    if chunk.file_path == node.file_path and chunk.start_line <= node.start_line and chunk.end_line >= node.end_line
                ),
                None,
            )
            if by_range:
                return by_range
        return next(
            (
                chunk for chunk in repository.chunks
                if chunk.file_path == node.file_path and (chunk.symbol_name == node.label or chunk.chunk_type == node.type)
            ),
            None,
        ) or self.file_summary_chunk(repository, node.file_path)

    def _idf_by_term(self, chunks: list[ChunkRecord], terms: list[str]) -> dict[str, float]:
        total = max(len(chunks), 1)
        result: dict[str, float] = {}
        for term in terms:
            frequency = sum(1 for chunk in chunks if term in set(self.tokens(self.chunk_haystack(chunk))))
            result[term] = log(1 + (total - frequency + 0.5) / (frequency + 0.5))
        return result

    def _bm25_score(self, terms: list[str], haystack: str, idf: dict[str, float], avg_len: float) -> float:
        tokens = self.tokens(haystack)
        if not tokens:
            return 0.0
        score = 0.0
        k1 = 1.2
        b = 0.75
        for term in terms:
            frequency = tokens.count(term)
            if frequency == 0:
                continue
            denominator = frequency + k1 * (1 - b + b * len(tokens) / max(avg_len, 1))
            score += idf.get(term, 0.0) * ((frequency * (k1 + 1)) / denominator)
        return score


class BaseRetriever:
    name: RetrieverName
    version = "1"

    def __init__(self, scorer: RetrievalScorer) -> None:
        self.scorer = scorer

    def retrieve(self, request: RetrievalRequest, repository: RepositoryState) -> list[RetrievalCandidate]:
        if repository.id != request.repository_id:
            raise ValueError("retrieval repository does not match request ownership")
        ordered = sorted(self.seeds(request, repository), key=lambda seed: (-seed.raw_score, seed.chunk.id, seed.title))
        seeds: list[CandidateSeed] = []
        seen_chunks: set[str] = set()
        for seed in ordered:
            if seed.chunk.id in seen_chunks:
                continue
            seen_chunks.add(seed.chunk.id)
            seeds.append(seed)
        candidates = [self._candidate(request, seed, rank) for rank, seed in enumerate(seeds, start=1)]
        for candidate in candidates:
            candidate.validate_ownership(request)
        return candidates

    def seeds(self, request: RetrievalRequest, repository: RepositoryState) -> list[CandidateSeed]:
        raise NotImplementedError

    def _candidate(self, request: RetrievalRequest, seed: CandidateSeed, rank: int) -> RetrievalCandidate:
        return RetrievalCandidate(
            candidate_id=candidate_id(request, self.name, seed.chunk),
            repository_id=request.repository_id,
            index_version_id=request.index_version_id,
            retriever=self.name,
            retriever_version=self.version,
            entity_key=f"chunk:v1:{seed.chunk.id}",
            source_key=f"file:v1:{seed.chunk.file_path}",
            raw_score=seed.raw_score,
            rank=rank,
            matched_terms=seed.matched_terms,
            reason_codes=seed.reason_codes,
            support_type=seed.support_type,
            provenance_refs=seed.provenance_refs,
            chunk=seed.chunk,
            result_type=seed.result_type,
            title=seed.title,
            compatibility_source=seed.compatibility_source,
        )


class LexicalRetriever(BaseRetriever):
    name = RetrieverName.LEXICAL

    def seeds(self, request: RetrievalRequest, repository: RepositoryState) -> list[CandidateSeed]:
        terms = self.scorer.query_terms(request.query)
        if not terms:
            return []
        return self.scorer.score_chunks(repository, terms, request.classification.compatibility_label, request.query)


class SymbolRetriever(BaseRetriever):
    name = RetrieverName.SYMBOL

    def seeds(self, request: RetrievalRequest, repository: RepositoryState) -> list[CandidateSeed]:
        terms = self.scorer.query_terms(request.query)
        seeds: list[CandidateSeed] = []
        for symbol in repository.symbols:
            score, matched = self.scorer.score_text(terms, self.scorer.symbol_haystack(symbol), request.query)
            chunk = self.scorer.chunk_for_symbol(repository, symbol)
            if score > 0 and chunk:
                seeds.append(CandidateSeed(chunk, score + 2.0, symbol.symbol_type, symbol.name, tuple(matched), ("symbol_match",), "symbol", SupportType.SOURCE_EXACT))
        return seeds


class EndpointRetriever(BaseRetriever):
    name = RetrieverName.ENDPOINT

    def seeds(self, request: RetrievalRequest, repository: RepositoryState) -> list[CandidateSeed]:
        terms = self.scorer.query_terms(request.query)
        seeds: list[CandidateSeed] = []
        for endpoint in repository.endpoints:
            score, matched = self.scorer.score_text(terms, self.scorer.endpoint_haystack(endpoint), request.query)
            chunk = self.scorer.chunk_for_endpoint(repository, endpoint)
            if score > 0 and chunk:
                seeds.append(CandidateSeed(chunk, score + 2.5, "endpoint", f"{endpoint.method} {endpoint.path}", tuple(matched), ("endpoint_match",), "endpoint", SupportType.SOURCE_EXACT))
        return seeds


class MetadataRetriever(BaseRetriever):
    name = RetrieverName.METADATA

    def seeds(self, request: RetrievalRequest, repository: RepositoryState) -> list[CandidateSeed]:
        terms = self.scorer.query_terms(request.query)
        seeds: list[CandidateSeed] = []
        for file_record in repository.files:
            score, matched = self.scorer.score_text(terms, self.scorer.file_haystack(file_record), request.query)
            chunk = self.scorer.file_summary_chunk(repository, file_record.path)
            if score > 0 and chunk:
                seeds.append(CandidateSeed(chunk, score + 1.0, "file", file_record.path, tuple(matched), ("file_metadata_match",), "file", SupportType.SOURCE_EXACT))
        return seeds


class GraphRetriever(BaseRetriever):
    name = RetrieverName.GRAPH

    def seeds(self, request: RetrievalRequest, repository: RepositoryState) -> list[CandidateSeed]:
        terms = self.scorer.query_terms(request.query)
        seeds: list[CandidateSeed] = []
        for node in repository.graph_nodes:
            score, matched = self.scorer.score_text(terms, self.scorer.graph_node_haystack(node), request.query)
            chunk = self.scorer.chunk_for_graph_node(repository, node)
            if score > 0 and chunk:
                seeds.append(CandidateSeed(chunk, score + 1.25, node.type, node.label, tuple(matched), ("graph_node_match",), "graph", SupportType.STATIC_RESOLVED))
        return seeds

    def related_candidates(
        self,
        request: RetrievalRequest,
        repository: RepositoryState,
        existing: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        matched_file_paths = {candidate.chunk.file_path for candidate in existing}
        existing_chunks = {candidate.chunk.id for candidate in existing}
        node_file_by_id = {node.id: node.file_path for node in repository.graph_nodes if node.file_path}
        related_files: set[str] = set()
        for edge in repository.graph_edges:
            source_file = node_file_by_id.get(edge.source)
            target_file = node_file_by_id.get(edge.target)
            if source_file in matched_file_paths and target_file:
                related_files.add(target_file)
            if target_file in matched_file_paths and source_file:
                related_files.add(source_file)
        seeds = [
            CandidateSeed(
                chunk=chunk,
                raw_score=1.25,
                result_type=chunk.chunk_type,
                title=chunk.symbol_name or Path(chunk.file_path).name,
                matched_terms=(),
                reason_codes=("graph_context_neighbor",),
                compatibility_source="graph_context",
                support_type=SupportType.STATIC_RESOLVED,
            )
            for chunk in repository.chunks
            if chunk.file_path in related_files
            and chunk.id not in existing_chunks
            and chunk.chunk_type in {"function", "method", "endpoint", "api_call", "file_summary"}
        ]
        ordered = sorted(seeds, key=lambda seed: (-seed.raw_score, seed.chunk.id, seed.title))
        graph_rank_offset = sum(1 for candidate in existing if candidate.retriever is RetrieverName.GRAPH)
        return [
            self._candidate(request, seed, rank)
            for rank, seed in enumerate(ordered, start=graph_rank_offset + 1)
        ]


class SemanticRetriever(BaseRetriever):
    name = RetrieverName.SEMANTIC

    def __init__(self, scorer: RetrievalScorer, vector_search: LocalVectorSearchService) -> None:
        super().__init__(scorer)
        self.vector_search = vector_search

    def seeds(self, request: RetrievalRequest, repository: RepositoryState) -> list[CandidateSeed]:
        return [
            CandidateSeed(
                chunk=match.chunk,
                raw_score=match.score * 6.5,
                result_type="file" if match.chunk.chunk_type in {"file_summary", "semantic_summary"} else match.chunk.chunk_type,
                title=match.chunk.symbol_name or Path(match.chunk.file_path).name,
                matched_terms=tuple(match.matched_terms),
                reason_codes=("semantic_sparse_vector_match",),
                compatibility_source="semantic_vector",
                support_type=SupportType.HEURISTIC,
            )
            for match in self.vector_search.search(repository, request.query, limit=max(request.limit * 2, 10))
        ]


class ExactRetriever(BaseRetriever):
    """Typed exact view over deterministic entity retrievers; compatibility scores stay unchanged."""

    name = RetrieverName.EXACT

    def __init__(self, scorer: RetrievalScorer, sources: tuple[BaseRetriever, ...]) -> None:
        super().__init__(scorer)
        self.sources = sources

    def seeds(self, request: RetrievalRequest, repository: RepositoryState) -> list[CandidateSeed]:
        query = request.query.lower()
        exact: dict[str, CandidateSeed] = {}
        for source in self.sources:
            for seed in source.seeds(request, repository):
                named_target = seed.title.lower() in query or seed.chunk.file_path.lower() in query
                if not named_target:
                    continue
                candidate = CandidateSeed(
                    chunk=seed.chunk,
                    raw_score=seed.raw_score,
                    result_type=seed.result_type,
                    title=seed.title,
                    matched_terms=seed.matched_terms,
                    reason_codes=("exact_named_target",),
                    compatibility_source=seed.compatibility_source,
                    support_type=seed.support_type,
                    provenance_refs=seed.provenance_refs,
                )
                existing = exact.get(seed.chunk.id)
                if existing is None or candidate.raw_score > existing.raw_score:
                    exact[seed.chunk.id] = candidate
        return list(exact.values())
