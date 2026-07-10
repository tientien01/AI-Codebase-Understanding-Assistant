from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import sqrt
import re

from app.services.index_models import ChunkRecord, RepositoryState


@dataclass(frozen=True)
class VectorSearchMatch:
    chunk: ChunkRecord
    score: float
    matched_terms: list[str]


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
