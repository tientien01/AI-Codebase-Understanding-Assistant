from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.services.chat.llm_client import LLMClient, LLMResult
from app.services.chat.ollama_client import OllamaClient
from app.services.chat.provider_context import ProviderEvidenceBlock, ProviderEvidenceContext


@dataclass
class FakeTransport:
    models: list[dict[str, object]] = field(
        default_factory=lambda: [{"name": "qwen2.5-coder:latest"}]
    )
    chat_content: str = '{"answer":"Grounded answer","citation_ids":["evidence_run"]}'
    fail: bool = False
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
        if self.fail:
            raise TimeoutError("local provider unavailable")
        if url.endswith("/api/tags"):
            return {"models": self.models}
        return {
            "done": True,
            "message": {"role": "assistant", "content": self.chat_content},
        }


def evidence_context() -> ProviderEvidenceContext:
    block = ProviderEvidenceBlock(
        evidence_id="evidence_run",
        repository_id="repo_test",
        index_version_id="idx_test",
        file_path="service.py",
        start_line=1,
        end_line=2,
        symbol_name="run",
        support_type="source_exact",
        content="def run():\n    return 1",
        token_estimate=16,
    )
    return ProviderEvidenceContext("repo_test", "idx_test", (block,), 100, 16)


@pytest.mark.parametrize(
    "base_url",
    [
        "https://127.0.0.1:11434",
        "http://example.com:11434",
        "http://user@127.0.0.1:11434",
        "http://127.0.0.1:11434/api",
        "http://127.0.0.1:11434?target=remote",
    ],
)
def test_ollama_rejects_non_loopback_or_ambiguous_origins(base_url: str) -> None:
    with pytest.raises(ValueError, match="Ollama base URL"):
        OllamaClient(base_url=base_url, model="qwen2.5-coder", timeout_seconds=10)


@pytest.mark.parametrize("model", ["", "../model", "model name", "model//tag"])
def test_ollama_rejects_invalid_model_identity(model: str) -> None:
    with pytest.raises(ValueError, match="model identity"):
        OllamaClient(
            base_url="http://127.0.0.1:11434",
            model=model,
            timeout_seconds=10,
        )


def test_readiness_distinguishes_ready_missing_and_unavailable() -> None:
    ready_transport = FakeTransport()
    ready = OllamaClient(
        base_url="http://localhost:11434/",
        model="qwen2.5-coder",
        timeout_seconds=12,
        transport=ready_transport,
    )

    assert ready.readiness().state == "ready"
    assert ready_transport.calls == [
        ("GET", "http://localhost:11434/api/tags", None, 12.0)
    ]

    missing = OllamaClient(
        base_url="http://[::1]:11434",
        model="missing-model",
        timeout_seconds=5,
        transport=FakeTransport(),
    )
    assert missing.readiness().state == "model_missing"

    unavailable = OllamaClient(
        base_url="http://127.0.0.1:11434",
        model="qwen2.5-coder",
        timeout_seconds=5,
        transport=FakeTransport(fail=True),
    )
    assert unavailable.readiness().state == "unavailable"


def test_native_chat_is_non_streaming_json_without_tools() -> None:
    transport = FakeTransport()
    client = OllamaClient(
        base_url="http://127.0.0.1:11434",
        model="qwen2.5-coder",
        timeout_seconds=10,
        transport=transport,
    )

    content = client.chat("system", "grounded prompt")

    assert content == transport.chat_content
    method, url, payload, timeout = transport.calls[0]
    assert (method, url, timeout) == ("POST", "http://127.0.0.1:11434/api/chat", 10.0)
    assert payload is not None
    assert payload["stream"] is False
    assert payload["format"] == "json"
    assert payload["think"] is False
    assert "tools" not in payload
    assert payload["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "grounded prompt"},
    ]


@pytest.mark.parametrize(
    "response",
    [
        {"done": False, "message": {"content": "partial"}},
        {"done": True, "message": {"content": ""}},
        {
            "done": True,
            "message": {"content": "{}", "tool_calls": [{"function": {"name": "run"}}]},
        },
        {"done": True, "message": "not-an-object"},
    ],
)
def test_native_chat_rejects_incomplete_empty_or_tool_payloads(
    response: dict[str, object]
) -> None:
    def transport(
        _method: str,
        _url: str,
        _payload: dict[str, object] | None,
        _timeout: float,
    ) -> dict[str, object]:
        return response

    client = OllamaClient(
        base_url="http://127.0.0.1:11434",
        model="qwen2.5-coder",
        timeout_seconds=10,
        transport=transport,
    )

    with pytest.raises(ValueError, match="Ollama returned"):
        client.chat("system", "prompt")


def test_llm_client_accepts_grounded_ollama_json_and_allowlisted_citation() -> None:
    transport = FakeTransport()
    client = LLMClient(
        provider="ollama",
        model="qwen2.5-coder",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_timeout_seconds=10,
        ollama_transport=transport,
    )

    result = client.generate_grounded_answer("Explain run", "code_question", evidence_context())

    assert result == LLMResult("Grounded answer", "ollama", ("evidence_run",))
    assert [call[0] for call in transport.calls] == ["GET", "POST"]
    chat_payload = transport.calls[1][2]
    assert chat_payload is not None
    assert "SOURCE_EVIDENCE_JSON_BEGIN" in chat_payload["messages"][1]["content"]  # type: ignore[index]


@pytest.mark.parametrize(
    ("transport", "expected_reason"),
    [
        (FakeTransport(models=[]), "configured_model_missing"),
        (FakeTransport(fail=True), "service_unavailable"),
    ],
)
def test_missing_or_unavailable_ollama_preserves_fallback(
    transport: FakeTransport, expected_reason: str
) -> None:
    client = LLMClient(
        provider="ollama",
        model="qwen2.5-coder",
        ollama_transport=transport,
    )

    assert client.provider_readiness().reason == expected_reason
    assert client.generate_grounded_answer(
        "Explain run", "code_question", evidence_context()
    ) is None


def test_invalid_configuration_and_provider_citations_fail_closed() -> None:
    invalid = LLMClient(
        provider="ollama",
        model="../model",
        ollama_base_url="http://remote.example:11434",
    )
    assert invalid.is_configured is False
    assert invalid.provider_readiness().reason == "invalid_configuration"

    bad_citation = LLMClient(
        provider="ollama",
        model="qwen2.5-coder",
        ollama_transport=FakeTransport(
            chat_content='{"answer":"Unsupported","citation_ids":["invented"]}'
        ),
    )
    assert bad_citation.generate_grounded_answer(
        "Explain run", "code_question", evidence_context()
    ) is None
