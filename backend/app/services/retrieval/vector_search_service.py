from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import sqrt
import re
from typing import Literal, Protocol

from app.services.embeddings.dense_index import DenseEmbeddingIndex, EmbeddingProvider
from app.services.embeddings.ollama import cosine_similarity
from app.services.index_models import ChunkRecord, RepositoryState


@dataclass(frozen=True)
class VectorSearchMatch:
    chunk: ChunkRecord
    score: float
    matched_terms: list[str]
    vector_kind: Literal["sparse", "dense"] = "sparse"


class VectorSearchProvider(Protocol):
    def search(
        self, repository: RepositoryState, query: str, limit: int = 10
    ) -> list[VectorSearchMatch]: ...


class LocalVectorSearchService:
    """Small deterministic vector search provider based on sparse token vectors."""

    def search(self, repository: RepositoryState, query: str, limit: int = 10) -> list[VectorSearchMatch]:
        query_vector = self._vector(query)
        if not query_vector:
            return []
        matches: list[VectorSearchMatch] = []
        for chunk in repository.chunks:
            chunk_text = f"{chunk.file_path} {chunk.symbol_name or ''} {chunk.chunk_type} {chunk.content}"
            chunk_vector = self._vector(chunk_text)
            score = self._cosine(query_vector, chunk_vector)
            if score <= 0:
                continue
            matches.append(
                VectorSearchMatch(
                    chunk=chunk,
                    score=score,
                    matched_terms=self._matched_terms(query_vector, chunk_vector),
                )
            )
        return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]

    def _vector(self, text: str) -> Counter[str]:
        tokens = self._tokens(text)
        vector: Counter[str] = Counter(tokens)
        for token in tokens:
            for subtoken in self._subtokens(token):
                vector[subtoken] += 0.35
        return vector

    def _tokens(self, text: str) -> list[str]:
        raw_tokens = re.findall(r"[A-Za-z0-9_/.-]+", text.lower())
        tokens: list[str] = []
        for token in raw_tokens:
            tokens.append(token)
            tokens.extend(part for part in re.split(r"[/_.-]+", token) if len(part) > 1)
        return tokens

    def _subtokens(self, token: str) -> list[str]:
        if len(token) < 5:
            return []
        return [token[index : index + 4] for index in range(0, len(token) - 3)]

    def _cosine(self, left: Counter[str], right: Counter[str]) -> float:
        shared = set(left) & set(right)
        numerator = sum(left[token] * right[token] for token in shared)
        if numerator <= 0:
            return 0.0
        left_norm = sqrt(sum(value * value for value in left.values()))
        right_norm = sqrt(sum(value * value for value in right.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def _matched_terms(self, left: Counter[str], right: Counter[str]) -> list[str]:
        return sorted((set(left) & set(right)), key=lambda token: (-left[token], token))[:8]


class DenseVectorSearchService:
    """Query one validated dense artifact; provider failure disables this view."""

    def __init__(self, index: DenseEmbeddingIndex, provider: EmbeddingProvider) -> None:
        self.index = index
        self.provider = provider

    def search(
        self, repository: RepositoryState, query: str, limit: int = 10
    ) -> list[VectorSearchMatch]:
        expected_index_id = f"idx_compat_{repository.current_index_version}"
        if (
            repository.id != self.index.repository_id
            or expected_index_id != self.index.index_version_id
            or limit <= 0
            or not query.strip()
        ):
            return []
        current_chunks = {item.id: item for item in repository.chunks}
        if sorted((item.id, item.content_hash) for item in repository.chunks) != [
            (item.chunk_id, item.content_hash) for item in self.index.chunks
        ]:
            return []
        try:
            identity = self.provider.identity()
            if (
                identity.resolved_model != self.index.model.resolved_model
                or identity.digest != self.index.model.digest
            ):
                return []
            batch = self.provider.embed((query,))
            if batch.dimension != self.index.model.dimension or len(batch.vectors) != 1:
                return []
            matches = [
                VectorSearchMatch(
                    chunk=current_chunks[item.chunk_id],
                    score=cosine_similarity(batch.vectors[0], item.vector),
                    matched_terms=[],
                    vector_kind="dense",
                )
                for item in self.index.chunks
            ]
        except Exception:
            return []
        matches = [item for item in matches if item.score > 0]
        return sorted(matches, key=lambda item: (-item.score, item.chunk.id))[:limit]
