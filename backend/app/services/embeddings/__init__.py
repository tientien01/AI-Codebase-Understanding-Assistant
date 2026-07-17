"""Versioned embedding provider and dense-index services."""

from app.services.embeddings.ollama import (
    EmbeddingBatch,
    EmbeddingModelIdentity,
    OllamaEmbeddingClient,
    cosine_similarity,
)

__all__ = [
    "EmbeddingBatch",
    "EmbeddingModelIdentity",
    "OllamaEmbeddingClient",
    "cosine_similarity",
]
