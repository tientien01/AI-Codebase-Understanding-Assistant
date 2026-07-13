from __future__ import annotations

from dataclasses import dataclass
import json

from app.core.config import settings
from app.schemas.api import CitationDTO


@dataclass(frozen=True)
class LLMResult:
    answer: str
    provider: str
    citation_ids: tuple[str, ...] = ()


class LLMClient:
    """Thin provider boundary for grounded chat answers."""

    def __init__(self, provider: str | None = None, model: str | None = None, api_key: str | None = None) -> None:
        self.provider = (provider or settings.llm_provider).lower()
        self.model = model or settings.llm_model
        self.api_key = api_key if api_key is not None else settings.llm_api_key

    @property
    def is_configured(self) -> bool:
        return self.provider != "fake" and bool(self.api_key)

    def generate_grounded_answer(self, question: str, question_type: str, citations: list[CitationDTO]) -> LLMResult | None:
        if not self.is_configured:
            return None
        if self.provider != "openai":
            return None

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        evidence = "\n".join(
            f"- {citation.evidence_id} {citation.file_path}:{citation.start_line}-{citation.end_line} "
            f"{citation.symbol_name or ''}".strip()
            for citation in citations
        )
        prompt = (
            "Answer using only the cited evidence. Return one JSON object with keys "
            "answer (string) and citation_ids (array chosen only from the supplied evidence IDs). "
            "If evidence is insufficient, return an empty citation_ids array and say what is missing.\n\n"
            f"Question type: {question_type}\n"
            f"Question: {question}\n"
            f"Evidence:\n{evidence}"
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a careful AI codebase assistant. Stay grounded in citations."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        return self.parse_grounded_response(
            content,
            self.provider,
            tuple(citation.evidence_id for citation in citations),
        )

    @staticmethod
    def parse_grounded_response(
        content: str,
        provider: str,
        allowed_citation_ids: tuple[str, ...],
    ) -> LLMResult | None:
        try:
            payload = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        answer = payload.get("answer")
        citation_ids = payload.get("citation_ids")
        if not isinstance(answer, str) or not answer.strip() or not isinstance(citation_ids, list):
            return None
        if any(not isinstance(item, str) for item in citation_ids):
            return None
        normalized = tuple(citation_ids)
        if not normalized or len(normalized) != len(set(normalized)):
            return None
        if not set(normalized).issubset(allowed_citation_ids):
            return None
        return LLMResult(answer.strip(), provider, normalized)
