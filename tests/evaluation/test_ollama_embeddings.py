from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.services.evaluation.ollama_embeddings import (
    OllamaEmbeddingClient,
    cosine_similarity,
)


@dataclass
class FakeTransport:
    embeddings: list[list[object]] = field(
        default_factory=lambda: [[1.0, 0.0], [0.0, 1.0]]
    )
    calls: list[tuple[str, str, dict[str, object] | None, float]] = field(
        default_factory=list
    )

    def __call__(
        self,
        method: str,
        url: str,
        payload: dict[str, object] | None,
        timeout: float,
    ) -> dict[str, object]:
        self.calls.append((method, url, payload, timeout))
        if url.endswith("/api/tags"):
            return {
                "models": [
                    {
                        "name": "embeddinggemma:latest",
                        "model": "embeddinggemma:latest",
                        "digest": "a" * 64,
                        "size": 622_000_000,
                        "capabilities": ["embedding"],
                    }
                ]
            }
        if url.endswith("/api/ps"):
            return {
                "models": [
                    {
                        "name": "embeddinggemma:latest",
                        "size": 700_000_000,
                        "size_vram": 650_000_000,
                        "context_length": 2_048,
                    }
                ]
            }
        count = len(payload["input"]) if payload and isinstance(payload.get("input"), list) else 0
        return {
            "embeddings": self.embeddings[:count],
            "total_duration": 10,
            "load_duration": 2,
            "prompt_eval_count": count,
        }


def test_embedding_client_freezes_identity_payload_dimension_and_memory() -> None:
    transport = FakeTransport()
    client = OllamaEmbeddingClient(
        base_url="http://127.0.0.1:11434",
        model="embeddinggemma",
        timeout_seconds=30,
        transport=transport,
    )

    identity = client.identity()
    batch = client.embed(("first", "second"))
    memory = client.memory()

    assert identity.resolved_model == "embeddinggemma:latest"
    assert identity.digest == "a" * 64
    assert batch.dimension == 2
    assert batch.vectors == ((1.0, 0.0), (0.0, 1.0))
    assert memory.observed_bytes == 700_000_000
    embed_payload = transport.calls[1][2]
    assert embed_payload == {
        "model": "embeddinggemma",
        "input": ["first", "second"],
        "truncate": False,
    }


@pytest.mark.parametrize(
    "vectors",
    [
        [],
        [[0.0, 0.0]],
        [[float("nan"), 1.0]],
        [["1", 0.0]],
        [[1.0], [1.0, 0.0]],
    ],
)
def test_embedding_client_rejects_malformed_vectors(vectors: list[list[object]]) -> None:
    client = OllamaEmbeddingClient(
        base_url="http://localhost:11434",
        model="embeddinggemma",
        transport=FakeTransport(embeddings=vectors),
    )
    inputs = ("one", "two") if len(vectors) == 2 else ("one",)

    with pytest.raises(ValueError, match="embedding"):
        client.embed(inputs)


def test_cosine_similarity_is_bounded_and_rejects_dimension_mismatch() -> None:
    assert cosine_similarity((1.0, 0.0), (1.0, 0.0)) == 1.0
    assert cosine_similarity((1.0, 0.0), (0.0, 1.0)) == 0.0
    with pytest.raises(ValueError, match="same non-zero dimension"):
        cosine_similarity((1.0,), (1.0, 0.0))
