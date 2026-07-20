from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.artifacts.store import FilesystemArtifactStore
from app.services.embeddings.dense_index import DenseIndexBuilder, DenseIndexLoader
from app.services.embeddings.ollama import EmbeddingBatch, EmbeddingModelIdentity
from app.services.index_models import ChunkRecord, RepositoryState
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.vector_search_service import DenseVectorSearchService


@dataclass
class FakeProvider:
    fail: bool = False
    digest: str = "d" * 64

    def identity(self) -> EmbeddingModelIdentity:
        return EmbeddingModelIdentity(
            "embeddinggemma",
            "embeddinggemma:latest",
            self.digest,
            1,
            ("embedding",),
        )

    def embed(self, inputs: tuple[str, ...]) -> EmbeddingBatch:
        if self.fail:
            raise RuntimeError("provider unavailable")
        vectors = tuple(
            (1.0, 0.0) if "auth" in item or "login" in item else (0.0, 1.0)
            for item in inputs
        )
        return EmbeddingBatch(vectors, 2, None, None, None)


def repository_fixture(tmp_path: Path) -> RepositoryState:
    return RepositoryState(
        id="repo_dense",
        name="dense-fixture",
        source_type="upload_folder",
        source_uri=None,
        source_path=tmp_path,
        current_index_version=1,
        chunks=[
            ChunkRecord(
                "chunk_auth",
                "auth.py",
                "function",
                "authenticate login token",
                1,
                3,
                "authenticate",
                content_hash="a" * 64,
            ),
            ChunkRecord(
                "chunk_cache",
                "cache.py",
                "function",
                "load cached profile",
                1,
                2,
                "load_profile",
                content_hash="b" * 64,
            ),
        ],
    )


def dense_retrieval(tmp_path: Path, *, provider: FakeProvider | None = None):
    repository = repository_fixture(tmp_path)
    provider = provider or FakeProvider()
    store = FilesystemArtifactStore(tmp_path / "artifacts")
    reference = DenseIndexBuilder(store, provider).build(
        repository.id,
        "idx_compat_1",
        repository.chunks,
    )
    index = DenseIndexLoader(store).load(
        reference,
        repository.chunks,
        expected_repository_id=repository.id,
        expected_index_version_id="idx_compat_1",
        expected_model=provider.identity(),
    )
    service = RetrievalService(DenseVectorSearchService(index, provider))
    return repository, service


def test_valid_dense_index_emits_semantic_candidates(tmp_path: Path) -> None:
    repository, service = dense_retrieval(tmp_path)

    _, candidates = service.retrieve_candidates(repository, "login", limit=5)
    semantic = [item for item in candidates if item.retriever.value == "semantic"]

    assert semantic
    assert semantic[0].chunk.id == "chunk_auth"
    assert semantic[0].compatibility_source == "semantic_dense"
    assert semantic[0].reason_codes == ("semantic_dense_vector_match",)


def test_dense_provider_failure_keeps_sparse_retrieval_available(tmp_path: Path) -> None:
    provider = FakeProvider()
    repository, service = dense_retrieval(tmp_path, provider=provider)
    provider.fail = True

    _, candidates = service.retrieve_candidates(repository, "login", limit=5)

    assert not [item for item in candidates if item.retriever.value == "semantic"]
    assert [item for item in candidates if item.retriever.value == "lexical"]


def test_stale_dense_index_keeps_sparse_retrieval_available(tmp_path: Path) -> None:
    repository, service = dense_retrieval(tmp_path)
    repository.chunks[0].content_hash = "c" * 64

    _, candidates = service.retrieve_candidates(repository, "login", limit=5)

    assert not [item for item in candidates if item.retriever.value == "semantic"]
    assert [item for item in candidates if item.retriever.value == "lexical"]


def test_changed_provider_model_keeps_sparse_retrieval_available(tmp_path: Path) -> None:
    provider = FakeProvider()
    repository, service = dense_retrieval(tmp_path, provider=provider)
    provider.digest = "e" * 64

    _, candidates = service.retrieve_candidates(repository, "login", limit=5)

    assert not [item for item in candidates if item.retriever.value == "semantic"]
    assert [item for item in candidates if item.retriever.value == "lexical"]
