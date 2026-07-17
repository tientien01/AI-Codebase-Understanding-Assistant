"""Bounded Ollama embedding adapter shared by evaluation and local retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Callable

from app.services.chat.ollama_client import (
    MAX_TIMEOUT_SECONDS,
    request_ollama_json,
    validate_ollama_base_url,
    validate_ollama_model,
)


MAX_EMBED_INPUTS = 64
MAX_EMBED_INPUT_BYTES = 65_536
MAX_EMBED_DIMENSIONS = 8_192
MAX_EMBED_RESPONSE_BYTES = 16 * 1_048_576

EmbeddingTransport = Callable[
    [str, str, dict[str, object] | None, float], dict[str, object]
]


@dataclass(frozen=True)
class EmbeddingModelIdentity:
    configured_model: str
    resolved_model: str
    digest: str
    size_bytes: int
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: tuple[tuple[float, ...], ...]
    dimension: int
    total_duration_ns: int | None
    load_duration_ns: int | None
    prompt_eval_count: int | None


@dataclass(frozen=True)
class ModelMemory:
    size_bytes: int | None
    size_vram_bytes: int | None
    context_length: int | None

    @property
    def observed_bytes(self) -> int | None:
        values = [item for item in (self.size_bytes, self.size_vram_bytes) if item is not None]
        return max(values) if values else None


class OllamaEmbeddingClient:
    """Validate and bound calls to a local Ollama embedding model."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 60.0,
        transport: EmbeddingTransport | None = None,
    ) -> None:
        self.base_url = validate_ollama_base_url(base_url)
        self.model = validate_ollama_model(model)
        if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
            raise ValueError("Ollama embedding timeout must be in (0, 120]")
        self.timeout_seconds = float(timeout_seconds)
        self._transport = transport or self._request_json

    def identity(self) -> EmbeddingModelIdentity:
        payload = self._transport("GET", f"{self.base_url}/api/tags", None, self.timeout_seconds)
        models = payload.get("models")
        if not isinstance(models, list):
            raise ValueError("Ollama tags response is invalid")
        accepted_names = {self.model}
        if ":" not in self.model:
            accepted_names.add(f"{self.model}:latest")
        matches = [
            item
            for item in models
            if isinstance(item, dict)
            and {item.get("name"), item.get("model")} & accepted_names
        ]
        if len(matches) != 1:
            raise ValueError("configured Ollama embedding model is missing or ambiguous")
        match = matches[0]
        resolved = match.get("model") or match.get("name")
        digest = match.get("digest")
        size = match.get("size")
        capabilities = match.get("capabilities")
        if (
            not isinstance(resolved, str)
            or not isinstance(digest, str)
            or len(digest) != 64
            or not isinstance(size, int)
            or size <= 0
            or not isinstance(capabilities, list)
            or any(not isinstance(item, str) for item in capabilities)
            or "embedding" not in capabilities
        ):
            raise ValueError("Ollama embedding model identity is invalid")
        return EmbeddingModelIdentity(
            configured_model=self.model,
            resolved_model=resolved,
            digest=digest,
            size_bytes=size,
            capabilities=tuple(sorted(capabilities)),
        )

    def embed(self, inputs: tuple[str, ...]) -> EmbeddingBatch:
        if not inputs or len(inputs) > MAX_EMBED_INPUTS:
            raise ValueError(f"embedding batch must contain 1..{MAX_EMBED_INPUTS} inputs")
        if any(
            not isinstance(item, str)
            or not item.strip()
            or len(item.encode("utf-8")) > MAX_EMBED_INPUT_BYTES
            for item in inputs
        ):
            raise ValueError("embedding input is blank or exceeds the byte limit")
        payload = self._transport(
            "POST",
            f"{self.base_url}/api/embed",
            {"model": self.model, "input": list(inputs), "truncate": False},
            self.timeout_seconds,
        )
        raw_vectors = payload.get("embeddings")
        if not isinstance(raw_vectors, list) or len(raw_vectors) != len(inputs):
            raise ValueError("Ollama embedding count does not match the input count")
        vectors: list[tuple[float, ...]] = []
        dimension: int | None = None
        for raw_vector in raw_vectors:
            if not isinstance(raw_vector, list) or not raw_vector:
                raise ValueError("Ollama embedding vector is empty")
            if any(
                not isinstance(value, (int, float)) or isinstance(value, bool)
                for value in raw_vector
            ):
                raise ValueError("Ollama embedding vector contains a non-numeric value")
            vector = tuple(float(value) for value in raw_vector)
            if any(not isfinite(value) for value in vector):
                raise ValueError("Ollama embedding vector contains a non-finite value")
            if not 0 < len(vector) <= MAX_EMBED_DIMENSIONS or sqrt(
                sum(value * value for value in vector)
            ) == 0:
                raise ValueError("Ollama embedding vector dimension or norm is invalid")
            dimension = dimension or len(vector)
            if len(vector) != dimension:
                raise ValueError("Ollama embedding dimensions are inconsistent")
            vectors.append(vector)
        return EmbeddingBatch(
            vectors=tuple(vectors),
            dimension=dimension or 0,
            total_duration_ns=_optional_non_negative_int(payload.get("total_duration")),
            load_duration_ns=_optional_non_negative_int(payload.get("load_duration")),
            prompt_eval_count=_optional_non_negative_int(payload.get("prompt_eval_count")),
        )

    def memory(self) -> ModelMemory:
        payload = self._transport("GET", f"{self.base_url}/api/ps", None, self.timeout_seconds)
        models = payload.get("models")
        if not isinstance(models, list):
            raise ValueError("Ollama running-model response is invalid")
        accepted_names = {self.model, f"{self.model}:latest"}
        for item in models:
            if isinstance(item, dict) and {item.get("name"), item.get("model")} & accepted_names:
                return ModelMemory(
                    size_bytes=_optional_non_negative_int(item.get("size")),
                    size_vram_bytes=_optional_non_negative_int(item.get("size_vram")),
                    context_length=_optional_non_negative_int(item.get("context_length")),
                )
        return ModelMemory(None, None, None)

    @staticmethod
    def _request_json(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        timeout_seconds: float,
    ) -> dict[str, object]:
        return request_ollama_json(
            method,
            url,
            payload,
            timeout_seconds,
            max_response_bytes=MAX_EMBED_RESPONSE_BYTES,
        )


def _optional_non_negative_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or value < 0:
        raise ValueError("Ollama metric must be a non-negative integer")
    return value


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("cosine vectors must have the same non-zero dimension")
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("cosine vectors must have non-zero norms")
    score = sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
    if not isfinite(score):
        raise ValueError("cosine score must be finite")
    return round(score, 12)
