from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.code_analysis.models import IRModule


class LanguageAdapter(ABC):
    language: str
    parser_version: str

    @abstractmethod
    def parse(self, repository_id: str, file_path: str, source: str) -> IRModule:
        """Parse source code into the language-independent IR."""
