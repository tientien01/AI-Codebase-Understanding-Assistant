from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.code_analysis.models import IRModule, ParseRequest


class LanguageAdapter(ABC):
    language: str
    parser_version: str

    @abstractmethod
    def parse(self, request: ParseRequest) -> IRModule:
        """Parse source code into the language-independent IR."""
