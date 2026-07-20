"""Compatibility exports for the RET-004 benchmark."""

from app.services.embeddings.ollama import (
    EmbeddingBatch,
    EmbeddingModelIdentity,
    EmbeddingTransport,
    MAX_EMBED_DIMENSIONS,
    MAX_EMBED_INPUT_BYTES,
    MAX_EMBED_INPUTS,
    MAX_EMBED_RESPONSE_BYTES,
    ModelMemory,
    OllamaEmbeddingClient,
    cosine_similarity,
)

__all__ = [
    "EmbeddingBatch",
    "EmbeddingModelIdentity",
    "EmbeddingTransport",
    "MAX_EMBED_DIMENSIONS",
    "MAX_EMBED_INPUT_BYTES",
    "MAX_EMBED_INPUTS",
    "MAX_EMBED_RESPONSE_BYTES",
    "ModelMemory",
    "OllamaEmbeddingClient",
    "cosine_similarity",
]
