from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.schemas.api import CitationDTO


@dataclass(frozen=True)
class LLMResult:
    answer: str
    provider: str


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
            f"- {citation.file_path}:{citation.start_line}-{citation.end_line} "
            f"{citation.symbol_name or ''}".strip()
            for citation in citations
        )
        prompt = (
            "Answer the user's codebase question using only the cited evidence. "
            "If the evidence is insufficient, say that clearly and list what is missing.\n\n"
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
        return LLMResult(answer=content.strip(), provider=self.provider)
