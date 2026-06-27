from __future__ import annotations

import re

from app.schemas.api import CitationDTO
from app.services.index_models import ChunkRecord, RepositoryState


class RetrievalService:
    def classify_question(self, question: str) -> str:
        normalized = question.lower()
        if any(token in normalized for token in ["kien truc", "architecture", "overview", "tong the"]):
            return "architecture_overview"
        if any(token in normalized for token in ["luong", "flow", "hoat dong"]):
            return "flow_tracing"
        if any(token in normalized for token in ["api", "endpoint", "post", "get"]):
            return "api_question"
        if any(token in normalized for token in ["database", "model", "table", "migration"]):
            return "database_question"
        if any(token in normalized for token in ["error", "loi", "401", "500", "exception"]):
            return "debugging"
        if any(token in normalized for token in ["doc file nao", "moi join", "onboarding"]):
            return "onboarding"
        if any(token in normalized for token in ["impact", "anh huong", "neu sua"]):
            return "impact_analysis"
        return "code_question"

    def search_chunks(self, repository: RepositoryState, query: str, limit: int) -> list[ChunkRecord]:
        terms = [term.lower() for term in re.findall(r"[\w/.-]+", query) if len(term) > 1]
        scored: list[ChunkRecord] = []
        for chunk in repository.chunks:
            haystack = f"{chunk.file_path} {chunk.symbol_name or ''} {chunk.content}".lower()
            score = sum(1.0 for term in terms if term in haystack)
            if chunk.symbol_name and chunk.symbol_name.lower() in query.lower():
                score += 2
            if chunk.file_path.lower() in query.lower():
                score += 2
            if chunk.chunk_type == "endpoint" and any(term in haystack for term in terms):
                score += 1
            if "login" in query.lower() and ("login" in haystack or "auth" in haystack):
                score += 3
            if any(token in query.lower() for token in ["overview", "kien truc", "architecture"]) and chunk.chunk_type in {"doc_section", "file_summary"}:
                score += 1
            if score > 0:
                clone = ChunkRecord(**{**chunk.__dict__, "score": min(0.99, score / max(len(terms), 1))})
                scored.append(clone)
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def generate_grounded_answer(self, question_type: str, message: str, citations: list[CitationDTO]) -> str:
        first = citations[0]
        if question_type == "flow_tracing":
            return (
                f"Luong xu ly co evidence chinh tai {first.file_path}:{first.start_line}-{first.end_line}. "
                "He thong tim cac endpoint, symbol va file lien quan trong index, sau do sap xep evidence theo do khop voi cau hoi. "
                "Cac buoc chi nen xem la grounded trong pham vi citation duoc tra ve."
            )
        if question_type == "debugging":
            return (
                f"Bat dau debug tu {first.file_path}:{first.start_line}-{first.end_line}, sau do kiem tra cac citation con lai. "
                "Neu loi lien quan config, he thong chi dung file config duoc index va khong doc .env that."
            )
        if question_type == "architecture_overview":
            return (
                "Kien truc duoc tom tat tu file source, README/docs va metadata parser. "
                f"Evidence manh nhat hien tai la {first.file_path}:{first.start_line}-{first.end_line}."
            )
        return (
            f"He thong tim thay evidence lien quan cho cau hoi '{message}'. "
            f"Ket luan chinh duoc neo vao {first.file_path}:{first.start_line}-{first.end_line} va cac citation kem theo."
        )
