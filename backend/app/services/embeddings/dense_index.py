"""Immutable, compatibility-bound dense embedding index artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from math import isfinite, sqrt
import re
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.artifacts.store import ArtifactStorePort, artifact_key
from app.services.embeddings.ollama import EmbeddingBatch, EmbeddingModelIdentity
from app.services.index_models import ChunkRecord


DENSE_INDEX_SCHEMA = "dense-embedding-index/v1"
DENSE_PREPROCESSING_VERSION = "chunk-text/v1"
MAX_DENSE_BATCH_SIZE = 64
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EmbeddingProvider(Protocol):
    def identity(self) -> EmbeddingModelIdentity: ...

    def embed(self, inputs: tuple[str, ...]) -> EmbeddingBatch: ...


class DenseIndexError(RuntimeError):
    """Stable failure for an unavailable or incompatible optional dense index."""


class DenseIndexModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DenseModelIdentity(DenseIndexModel):
    resolved_model: str = Field(min_length=1, max_length=256)
    digest: str
    dimension: int = Field(gt=0, le=8_192)

    @field_validator("digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("model digest must be lowercase SHA-256")
        return value


class DenseChunkVector(DenseIndexModel):
    chunk_id: str = Field(min_length=1, max_length=256)
    content_hash: str
    vector: tuple[float, ...]

    @field_validator("content_hash")
    @classmethod
    def validate_content_hash(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("chunk content_hash must be lowercase SHA-256")
        return value

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if not value or any(not isfinite(item) for item in value):
            raise ValueError("dense vector must be non-empty and finite")
        if sqrt(sum(item * item for item in value)) == 0:
            raise ValueError("dense vector norm must be non-zero")
        return value


class DenseEmbeddingIndex(DenseIndexModel):
    schema_version: str = DENSE_INDEX_SCHEMA
    repository_id: str
    index_version_id: str
    preprocessing_version: str = Field(min_length=1, max_length=128)
    model: DenseModelIdentity
    chunks: tuple[DenseChunkVector, ...]

    @model_validator(mode="after")
    def validate_index(self) -> "DenseEmbeddingIndex":
        artifact_key(
            self.repository_id,
            self.index_version_id,
            "dense_embedding_index",
            "index.json",
        )
        if self.schema_version != DENSE_INDEX_SCHEMA:
            raise ValueError("unsupported dense index schema")
        ids = [item.chunk_id for item in self.chunks]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("dense chunks must have unique canonical ordering")
        if any(len(item.vector) != self.model.dimension for item in self.chunks):
            raise ValueError("dense vector dimension does not match index identity")
        return self

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


@dataclass(frozen=True)
class DenseIndexReference:
    repository_id: str
    index_version_id: str
    key: str
    sha256: str
    byte_size: int
    records: int
    model: DenseModelIdentity
    preprocessing_version: str


def chunk_embedding_text(chunk: ChunkRecord) -> str:
    """Produce the declared v1 embedding input without reading source again."""
    symbol = chunk.symbol_name or ""
    return "\n".join((chunk.file_path, chunk.chunk_type, symbol, chunk.content))


class DenseIndexBuilder:
    def __init__(self, store: ArtifactStorePort, provider: EmbeddingProvider) -> None:
        self.store = store
        self.provider = provider

    def build(
        self,
        repository_id: str,
        index_version_id: str,
        chunks: list[ChunkRecord],
        *,
        batch_size: int = 32,
        preprocessing_version: str = DENSE_PREPROCESSING_VERSION,
    ) -> DenseIndexReference:
        if not 0 < batch_size <= MAX_DENSE_BATCH_SIZE:
            raise ValueError(f"dense batch_size must be in 1..{MAX_DENSE_BATCH_SIZE}")
        ordered = sorted(chunks, key=lambda item: item.id)
        if not ordered or len({item.id for item in ordered}) != len(ordered):
            raise DenseIndexError("dense index requires unique chunks")
        if any(not SHA256.fullmatch(item.content_hash) for item in ordered):
            raise DenseIndexError("dense index requires versioned chunk content hashes")

        identity = self.provider.identity()
        vectors: list[tuple[float, ...]] = []
        dimension: int | None = None
        for offset in range(0, len(ordered), batch_size):
            batch_chunks = ordered[offset : offset + batch_size]
            batch = self.provider.embed(tuple(chunk_embedding_text(item) for item in batch_chunks))
            if len(batch.vectors) != len(batch_chunks):
                raise DenseIndexError("embedding provider returned an incomplete batch")
            dimension = dimension or batch.dimension
            if batch.dimension != dimension:
                raise DenseIndexError("embedding dimension changed during index build")
            vectors.extend(batch.vectors)

        model = DenseModelIdentity(
            resolved_model=identity.resolved_model,
            digest=identity.digest,
            dimension=dimension or 0,
        )
        index = DenseEmbeddingIndex(
            repository_id=repository_id,
            index_version_id=index_version_id,
            preprocessing_version=preprocessing_version,
            model=model,
            chunks=tuple(
                DenseChunkVector(
                    chunk_id=chunk.id,
                    content_hash=chunk.content_hash,
                    vector=vector,
                )
                for chunk, vector in zip(ordered, vectors, strict=True)
            ),
        )
        payload = index.canonical_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        key = artifact_key(
            repository_id,
            index_version_id,
            "dense_embedding_index",
            "index.json",
        )
        stored = self.store.write(
            key,
            [payload],
            expected_sha256=digest,
            expected_size=len(payload),
        )
        return DenseIndexReference(
            repository_id=repository_id,
            index_version_id=index_version_id,
            key=stored.key,
            sha256=stored.sha256,
            byte_size=stored.byte_size,
            records=len(index.chunks),
            model=model,
            preprocessing_version=preprocessing_version,
        )


class DenseIndexLoader:
    def __init__(self, store: ArtifactStorePort) -> None:
        self.store = store

    def load(
        self,
        reference: DenseIndexReference,
        chunks: list[ChunkRecord],
        *,
        expected_repository_id: str,
        expected_index_version_id: str,
        expected_model: EmbeddingModelIdentity,
        expected_preprocessing_version: str = DENSE_PREPROCESSING_VERSION,
    ) -> DenseEmbeddingIndex:
        expected_key = artifact_key(
            expected_repository_id,
            expected_index_version_id,
            "dense_embedding_index",
            "index.json",
        )
        if (
            reference.repository_id != expected_repository_id
            or reference.index_version_id != expected_index_version_id
            or reference.key != expected_key
            or reference.preprocessing_version != expected_preprocessing_version
            or reference.model.resolved_model != expected_model.resolved_model
            or reference.model.digest != expected_model.digest
        ):
            raise DenseIndexError("dense index reference is stale or incompatible")
        try:
            payload = self.store.read_bytes(
                reference.key,
                expected_sha256=reference.sha256,
                expected_size=reference.byte_size,
            )
            index = DenseEmbeddingIndex.model_validate_json(payload)
        except Exception as exc:
            raise DenseIndexError("dense index artifact is missing, corrupt or invalid") from exc
        expected_chunks = sorted((item.id, item.content_hash) for item in chunks)
        actual_chunks = [(item.chunk_id, item.content_hash) for item in index.chunks]
        if (
            index.repository_id != expected_repository_id
            or index.index_version_id != expected_index_version_id
            or index.preprocessing_version != expected_preprocessing_version
            or index.model != reference.model
            or actual_chunks != expected_chunks
            or len(index.chunks) != reference.records
        ):
            raise DenseIndexError("dense index requires rebuild")
        return index
