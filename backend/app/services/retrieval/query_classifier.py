from __future__ import annotations

from app.services.retrieval.contracts import QueryClassification, QuestionType


CLASSIFICATION_RULES: tuple[tuple[QuestionType, tuple[str, ...]], ...] = (
    (QuestionType.ARCHITECTURE_OVERVIEW, ("kien truc", "architecture", "overview", "tong the")),
    (QuestionType.FLOW_TRACING, ("luong", "flow", "hoat dong")),
    (QuestionType.API_QUESTION, ("api", "endpoint", "post", "get")),
    (QuestionType.DATABASE_QUESTION, ("database", "model", "table", "migration")),
    (QuestionType.DEBUGGING, ("error", "loi", "401", "500", "exception")),
    (QuestionType.ONBOARDING, ("doc file nao", "moi join", "onboarding")),
    (QuestionType.IMPACT_ANALYSIS, ("impact", "anh huong", "neu sua")),
)


class QueryClassifier:
    """Deterministic compatibility classifier with typed output and stable reasons."""

    VERSION = "1"

    def classify(self, question: str) -> QueryClassification:
        normalized = question.lower()
        for question_type, signals in CLASSIFICATION_RULES:
            matched = tuple(signal for signal in signals if signal in normalized)
            if matched:
                return QueryClassification(
                    question_type=question_type,
                    confidence=0.9,
                    reason_codes=tuple(f"matched:{signal}" for signal in matched),
                )
        return QueryClassification(
            question_type=QuestionType.CODE_QUESTION,
            confidence=0.5,
            reason_codes=("default:code_question",),
        )
