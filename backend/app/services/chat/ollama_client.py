from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import re
from typing import Callable, Literal
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_RESPONSE_BYTES = 1_048_576
MAX_TIMEOUT_SECONDS = 120.0
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


@dataclass(frozen=True)
class OllamaReadiness:
    state: Literal["ready", "unavailable", "model_missing"]
    reason: str


OllamaTransport = Callable[[str, str, dict[str, object] | None, float], dict[str, object]]


class _NoRedirectHandler(HTTPRedirectHandler):
    """Prevent a compromised local daemon from redirecting requests off-host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class OllamaClient:
    """Minimal native Ollama adapter restricted to a loopback HTTP endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: OllamaTransport | None = None,
    ) -> None:
        self.base_url = self._validate_base_url(base_url)
        self.model = self._validate_model(model)
        if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
            raise ValueError("Ollama timeout must be greater than zero and at most 120 seconds")
        self.timeout_seconds = float(timeout_seconds)
        self._transport = transport or self._request_json

    def readiness(self) -> OllamaReadiness:
        try:
            payload = self._transport("GET", f"{self.base_url}/api/tags", None, self.timeout_seconds)
            models = self._model_names(payload)
        except Exception:
            return OllamaReadiness("unavailable", "service_unavailable")
        if not self._matches_configured_model(models):
            return OllamaReadiness("model_missing", "configured_model_missing")
        return OllamaReadiness("ready", "configured_model_available")

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "think": False,
            "options": {"temperature": 0.1},
        }
        response = self._transport(
            "POST", f"{self.base_url}/api/chat", payload, self.timeout_seconds
        )
        message = response.get("message")
        if response.get("done") is not True or not isinstance(message, dict):
            raise ValueError("Ollama returned an incomplete chat response")
        if message.get("tool_calls"):
            raise ValueError("Ollama returned unrequested tool calls")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama returned empty chat content")
        return content

    @staticmethod
    def _validate_base_url(value: str) -> str:
        parsed = urlparse(value.strip())
        if (
            parsed.scheme != "http"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("Ollama base URL must be a credential-free loopback HTTP origin")
        try:
            is_loopback = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            is_loopback = parsed.hostname.lower() == "localhost"
        if not is_loopback:
            raise ValueError("Ollama base URL must use localhost or a loopback IP literal")
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Ollama base URL has an invalid port") from exc
        authority = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        if port is not None:
            authority = f"{authority}:{port}"
        return f"http://{authority}"

    @staticmethod
    def _validate_model(value: str) -> str:
        model = value.strip()
        if not MODEL_PATTERN.fullmatch(model) or ".." in model or "//" in model:
            raise ValueError("Ollama model identity is invalid")
        return model

    @staticmethod
    def _model_names(payload: dict[str, object]) -> set[str]:
        raw_models = payload.get("models")
        if not isinstance(raw_models, list):
            raise ValueError("Ollama tags response is invalid")
        names: set[str] = set()
        for item in raw_models:
            if not isinstance(item, dict):
                raise ValueError("Ollama model entry is invalid")
            for key in ("name", "model"):
                value = item.get(key)
                if isinstance(value, str) and value:
                    names.add(value)
        return names

    def _matches_configured_model(self, models: set[str]) -> bool:
        if self.model in models:
            return True
        return ":" not in self.model and f"{self.model}:latest" in models

    @staticmethod
    def _request_json(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        timeout_seconds: float,
    ) -> dict[str, object]:
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
        request = Request(
            url,
            data=body,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        opener = build_opener(_NoRedirectHandler())
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            raise RuntimeError("Ollama request failed") from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Ollama response exceeds the size limit")
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("Ollama response must be a JSON object")
        return decoded
