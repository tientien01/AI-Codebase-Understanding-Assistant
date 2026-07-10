from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from math import log
from pathlib import Path
import re

from app.schemas.api import CitationDTO
from app.services.index_models import ChunkRecord, EndpointRecord, FileRecord, RepositoryState, SymbolRecord

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "what",
    "where",
    "when",
    "how",
    "can",
    "you",
    "toi",
    "cua",
    "cho",
    "nao",
    "nhu",
    "the",
    "hoat",
    "dong",
}

QUESTION_TYPE_CHUNK_BOOSTS = {
    "api_question": {"endpoint": 2.0, "function": 0.5, "method": 0.5},
    "flow_tracing": {"endpoint": 1.0, "function": 1.0, "method": 1.0},
    "architecture_overview": {"doc_section": 1.5, "file_summary": 1.0},
    "debugging": {"function": 0.8, "method": 0.8, "file_summary": 0.4},
}


@dataclass(frozen=True)
class HybridSearchMatch:
    chunk: ChunkRecord
    score: float
    result_type: str
    retrieval_source: str
    title: str
    matched_terms: list[str]


class RetrievalService:
    def classify_question(self, question: str) -> str:
        normalized = question.lower()
        if any(token in normalized for token in ["kien truc", "architecture", "overview", "tong the"]):
            return "architecture_overview"
        if any(token in normalized for token in ["luong", "flow", "hoat dong"]):
            return "flow_tracing"
        if any(token in normalized for token in ["api", "endpoint", "post", "get"]):
            return "api_question"
        if any(token in normalized for token in ["database", "model", "table", "migration"]):
            return "database_question"
        if any(token in normalized for token in ["error", "loi", "401", "500", "exception"]):
            return "debugging"
        if any(token in normalized for token in ["doc file nao", "moi join", "onboarding"]):
            return "onboarding"
        if any(token in normalized for token in ["impact", "anh huong", "neu sua"]):
            return "impact_analysis"
        return "code_question"

    def search_chunks(self, repository: RepositoryState, query: str, limit: int) -> list[ChunkRecord]:
        return [
            ChunkRecord(**{**match.chunk.__dict__, "score": match.score})
            for match in self.hybrid_search(repository, query, limit)
        ]

    def hybrid_search(self, repository: RepositoryState, query: str, limit: int) -> list[HybridSearchMatch]:
        question_type = self.classify_question(query)
        terms = self._query_terms(query)
        if not terms:
            return []

        matches: dict[str, HybridSearchMatch] = {}
        chunk_scores = self._score_chunks(repository, terms, question_type, query)
        for chunk, score, source, matched_terms in chunk_scores:
            result_type = "file" if chunk.chunk_type == "file_summary" else chunk.chunk_type
            self._upsert_match(
                matches,
                chunk,
                score,
                result_type,
                source,
                chunk.symbol_name or Path(chunk.file_path).name,
                matched_terms,
            )

        for symbol in repository.symbols:
            score, matched_terms = self._score_text(terms, self._symbol_haystack(symbol), query)
            if score <= 0:
                continue
            chunk = self._chunk_for_symbol(repository, symbol)
            if chunk:
                self._upsert_match(matches, chunk, score + 2.0, symbol.symbol_type, "symbol", symbol.name, matched_terms)

        for endpoint in repository.endpoints:
            score, matched_terms = self._score_text(terms, self._endpoint_haystack(endpoint), query)
            if score <= 0:
                continue
            chunk = self._chunk_for_endpoint(repository, endpoint)
            if chunk:
                title = f"{endpoint.method} {endpoint.path}"
                self._upsert_match(matches, chunk, score + 2.5, "endpoint", "endpoint", title, matched_terms)

        for file_record in repository.files:
            score, matched_terms = self._score_text(terms, self._file_haystack(file_record), query)
            if score <= 0:
                continue
            chunk = self._file_summary_chunk(repository, file_record.path)
            if chunk:
                self._upsert_match(matches, chunk, score + 1.0, "file", "file", file_record.path, matched_terms)

        for node in repository.graph_nodes:
            score, matched_terms = self._score_text(terms, self._graph_node_haystack(node), query)
            if score <= 0:
                continue
            chunk = self._chunk_for_graph_node(repository, node)
            if chunk:
                self._upsert_match(matches, chunk, score + 1.25, node.type, "graph", node.label, matched_terms)

        self._apply_graph_context_boost(repository, matches)
        ranked = sorted(matches.values(), key=lambda item: item.score, reverse=True)
        return ranked[:limit]

    def _score_chunks(
        self,
        repository: RepositoryState,
        terms: list[str],
        question_type: str,
        query: str,
    ) -> list[tuple[ChunkRecord, float, str, list[str]]]:
        idf = self._idf_by_term(repository.chunks, terms)
        avg_len = sum(len(self._tokens(self._chunk_haystack(chunk))) for chunk in repository.chunks) / max(len(repository.chunks), 1)
        scored: list[tuple[ChunkRecord, float, str, list[str]]] = []
        for chunk in repository.chunks:
            haystack = self._chunk_haystack(chunk)
            score = self._bm25_score(terms, haystack, idf, avg_len)
            score += self._lexical_score(terms, haystack) * 0.65
            score += self._fuzzy_score(terms, haystack) * 0.8
            score += QUESTION_TYPE_CHUNK_BOOSTS.get(question_type, {}).get(chunk.chunk_type, 0.0)
            normalized_query = query.lower()
            if chunk.symbol_name and chunk.symbol_name.lower() in normalized_query:
                score += 3
            if chunk.file_path.lower() in normalized_query:
                score += 3
            if chunk.chunk_type == "endpoint" and any(term in haystack for term in terms):
                score += 1
            if "login" in normalized_query and ("login" in haystack or "auth" in haystack):
                score += 3
            if score > 0:
                scored.append((chunk, score, "chunk", self._matched_terms(terms, haystack)))
        return scored

    def _query_terms(self, query: str) -> list[str]:
        raw_terms = re.findall(r"[\w/.-]+", query.lower())
        deduped: list[str] = []
        seen: set[str] = set()
        for term in raw_terms:
            if len(term) <= 1 or term in STOPWORDS or term in seen:
                continue
            seen.add(term)
            deduped.append(term)
        return deduped

    def _chunk_haystack(self, chunk: ChunkRecord) -> str:
        return f"{chunk.file_path} {chunk.symbol_name or ''} {chunk.chunk_type} {chunk.content}".lower()

    def _lexical_score(self, terms: list[str], haystack: str) -> float:
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

    def _score_text(self, terms: list[str], haystack: str, query: str) -> tuple[float, list[str]]:
        normalized = haystack.lower()
        score = self._lexical_score(terms, normalized) + self._fuzzy_score(terms, normalized)
        if query.lower().strip() and query.lower().strip() in normalized:
            score += 2.0
        return score, self._matched_terms(terms, normalized)

    def _fuzzy_score(self, terms: list[str], haystack: str) -> float:
        tokens = self._tokens(haystack)
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

    def _idf_by_term(self, chunks: list[ChunkRecord], terms: list[str]) -> dict[str, float]:
        total = max(len(chunks), 1)
        result: dict[str, float] = {}
        for term in terms:
            document_frequency = sum(1 for chunk in chunks if term in set(self._tokens(self._chunk_haystack(chunk))))
            result[term] = log(1 + (total - document_frequency + 0.5) / (document_frequency + 0.5))
        return result

    def _bm25_score(self, terms: list[str], haystack: str, idf: dict[str, float], avg_len: float) -> float:
        tokens = self._tokens(haystack)
        if not tokens:
            return 0.0
        token_count = len(tokens)
        score = 0.0
        k1 = 1.2
        b = 0.75
        for term in terms:
            frequency = tokens.count(term)
            if frequency == 0:
                continue
            denominator = frequency + k1 * (1 - b + b * token_count / max(avg_len, 1))
            score += idf.get(term, 0.0) * ((frequency * (k1 + 1)) / denominator)
        return score

    def _tokens(self, text: str) -> list[str]:
        return re.findall(r"[\w/.-]+", text.lower())

    def _matched_terms(self, terms: list[str], haystack: str) -> list[str]:
        tokens = set(self._tokens(haystack))
        return [term for term in terms if term in tokens or term in haystack]

    def _symbol_haystack(self, symbol: SymbolRecord) -> str:
        return f"{symbol.name} {symbol.symbol_type} {symbol.signature} {symbol.file_path}".lower()

    def _endpoint_haystack(self, endpoint: EndpointRecord) -> str:
        metadata = " ".join(f"{key} {value}" for key, value in endpoint.metadata.items())
        return f"{endpoint.method} {endpoint.path} {endpoint.handler} {endpoint.file_path} {metadata}".lower()

    def _file_haystack(self, file_record: FileRecord) -> str:
        return f"{file_record.path} {Path(file_record.path).name} {file_record.language} {file_record.file_type}".lower()

    def _graph_node_haystack(self, node) -> str:
        return " ".join(
            [
                node.label,
                node.type,
                node.file_path or "",
                node.role or "",
                node.summary or "",
                node.layer or "",
                " ".join(node.tags),
            ]
        ).lower()

    def _chunk_for_symbol(self, repository: RepositoryState, symbol: SymbolRecord) -> ChunkRecord | None:
        return next(
            (
                chunk
                for chunk in repository.chunks
                if chunk.file_path == symbol.file_path
                and (
                    chunk.symbol_name == symbol.name
                    or (chunk.start_line == symbol.start_line and chunk.end_line == symbol.end_line)
                )
            ),
            None,
        )

    def _chunk_for_endpoint(self, repository: RepositoryState, endpoint: EndpointRecord) -> ChunkRecord | None:
        return next(
            (
                chunk
                for chunk in repository.chunks
                if chunk.file_path == endpoint.file_path
                and chunk.chunk_type == "endpoint"
                and (chunk.symbol_name == endpoint.handler or endpoint.path in chunk.content)
            ),
            None,
        )

    def _file_summary_chunk(self, repository: RepositoryState, file_path: str) -> ChunkRecord | None:
        return next(
            (
                chunk
                for chunk in repository.chunks
                if chunk.file_path == file_path and chunk.chunk_type == "file_summary"
            ),
            None,
        ) or next((chunk for chunk in repository.chunks if chunk.file_path == file_path), None)

    def _chunk_for_graph_node(self, repository: RepositoryState, node) -> ChunkRecord | None:
        if not node.file_path:
            return None
        if node.start_line is not None and node.end_line is not None:
            by_range = next(
                (
                    chunk
                    for chunk in repository.chunks
                    if chunk.file_path == node.file_path
                    and chunk.start_line <= node.start_line
                    and chunk.end_line >= node.end_line
                ),
                None,
            )
            if by_range:
                return by_range
        return next(
            (
                chunk
                for chunk in repository.chunks
                if chunk.file_path == node.file_path and (chunk.symbol_name == node.label or chunk.chunk_type == node.type)
            ),
            None,
        ) or self._file_summary_chunk(repository, node.file_path)

    def _upsert_match(
        self,
        matches: dict[str, HybridSearchMatch],
        chunk: ChunkRecord,
        raw_score: float,
        result_type: str,
        retrieval_source: str,
        title: str,
        matched_terms: list[str],
    ) -> None:
        score = round(min(0.99, raw_score / 8.0), 4)
        scored_chunk = ChunkRecord(**{**chunk.__dict__, "score": score})
        existing = matches.get(chunk.id)
        if existing is None or score > existing.score:
            matches[chunk.id] = HybridSearchMatch(
                chunk=scored_chunk,
                score=score,
                result_type=result_type,
                retrieval_source=retrieval_source,
                title=title,
                matched_terms=matched_terms,
            )

    def _apply_graph_context_boost(self, repository: RepositoryState, matches: dict[str, HybridSearchMatch]) -> None:
        if not matches:
            return
        matched_file_paths = {match.chunk.file_path for match in matches.values()}
        related_files: set[str] = set()
        node_file_by_id = {node.id: node.file_path for node in repository.graph_nodes if node.file_path}
        for edge in repository.graph_edges:
            source_file = node_file_by_id.get(edge.source)
            target_file = node_file_by_id.get(edge.target)
            if source_file in matched_file_paths and target_file:
                related_files.add(target_file)
            if target_file in matched_file_paths and source_file:
                related_files.add(source_file)

        for chunk in repository.chunks:
            if chunk.file_path not in related_files or chunk.id in matches:
                continue
            if chunk.chunk_type not in {"function", "method", "endpoint", "api_call", "file_summary"}:
                continue
            self._upsert_match(
                matches,
                chunk,
                raw_score=1.25,
                result_type=chunk.chunk_type,
                retrieval_source="graph_context",
                title=chunk.symbol_name or Path(chunk.file_path).name,
                matched_terms=[],
            )

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
