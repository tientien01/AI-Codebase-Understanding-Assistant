from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.services.artifacts.store import FilesystemArtifactStore
from app.services.embeddings.dense_index import (
    DENSE_PREPROCESSING_VERSION,
    DenseIndexBuilder,
    DenseIndexError,
    DenseIndexLoader,
)
from app.services.embeddings.ollama import EmbeddingBatch, EmbeddingModelIdentity
from app.services.index_models import ChunkRecord


def chunks() -> list[ChunkRecord]:
    return [
        ChunkRecord(
            "chunk_b",
            "cache.py",
            "function",
            "load cached profile",
            1,
            2,
            "load_profile",
            content_hash="b" * 64,
        ),
        ChunkRecord(
            "chunk_a",
            "auth.py",
            "function",
            "authenticate login token",
            1,
            3,
            "authenticate",
            content_hash="a" * 64,
        ),
    ]


@dataclass
class FakeProvider:
    digest: str = "d" * 64
    fail: bool = False

    def identity(self) -> EmbeddingModelIdentity:
        return EmbeddingModelIdentity(
            configured_model="embeddinggemma",
            resolved_model="embeddinggemma:latest",
            digest=self.digest,
            size_bytes=1,
            capabilities=("embedding",),
        )

    def embed(self, inputs: tuple[str, ...]) -> EmbeddingBatch:
        if self.fail:
            raise RuntimeError("provider unavailable")
        vectors = tuple(
            (1.0, 0.0) if "auth" in item or "login" in item else (0.0, 1.0)
            for item in inputs
        )
        return EmbeddingBatch(vectors, 2, None, None, None)


def build_index(tmp_path: Path):
    store = FilesystemArtifactStore(tmp_path / "artifacts")
    provider = FakeProvider()
    reference = DenseIndexBuilder(store, provider).build(
        "repo_dense",
        "idx_compat_1",
        chunks(),
        batch_size=2,
    )
    return store, provider, reference


def test_build_is_canonical_immutable_and_loads_compatible_index(tmp_path: Path) -> None:
    store, provider, first = build_index(tmp_path)
    second = DenseIndexBuilder(store, provider).build(
        "repo_dense", "idx_compat_1", list(reversed(chunks())), batch_size=1
    )

    assert first == second
    index = DenseIndexLoader(store).load(
        first,
        chunks(),
        expected_repository_id="repo_dense",
        expected_index_version_id="idx_compat_1",
        expected_model=provider.identity(),
    )
    assert [item.chunk_id for item in index.chunks] == ["chunk_a", "chunk_b"]
    assert index.preprocessing_version == DENSE_PREPROCESSING_VERSION
    assert index.model.dimension == 2


@pytest.mark.parametrize("change", ["model", "content", "version"])
def test_loader_requires_rebuild_for_incompatible_identity(
    tmp_path: Path, change: str
) -> None:
    store, provider, reference = build_index(tmp_path)
    current_chunks = chunks()
    expected_model = provider.identity()
    expected_version = "idx_compat_1"
    if change == "model":
        expected_model = FakeProvider(digest="e" * 64).identity()
    elif change == "content":
        current_chunks[0].content_hash = "c" * 64
    else:
        expected_version = "idx_compat_2"

    with pytest.raises(DenseIndexError, match="stale|rebuild"):
        DenseIndexLoader(store).load(
            reference,
            current_chunks,
            expected_repository_id="repo_dense",
            expected_index_version_id=expected_version,
            expected_model=expected_model,
        )


def test_provider_failure_never_publishes_partial_artifact(tmp_path: Path) -> None:
    store = FilesystemArtifactStore(tmp_path / "artifacts")

    with pytest.raises(RuntimeError, match="unavailable"):
        DenseIndexBuilder(store, FakeProvider(fail=True)).build(
            "repo_dense", "idx_compat_1", chunks()
        )

    assert not (tmp_path / "artifacts").exists()


def test_loader_rejects_corrupt_artifact(tmp_path: Path) -> None:
    store, provider, reference = build_index(tmp_path)
    artifact_path = tmp_path / "artifacts" / Path(*reference.key.split("/"))
    artifact_path.write_bytes(b"corrupt")

    with pytest.raises(DenseIndexError, match="corrupt"):
        DenseIndexLoader(store).load(
            reference,
            chunks(),
            expected_repository_id="repo_dense",
            expected_index_version_id="idx_compat_1",
            expected_model=provider.identity(),
        )
