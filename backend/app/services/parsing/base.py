from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.index_models import FileRecord, RepositoryState


class LanguageParser(ABC):
    @abstractmethod
    def parse(self, repository: RepositoryState, file_record: FileRecord, text: str) -> None:
        """Extract symbols, chunks, endpoints, and graph hints from a file."""

