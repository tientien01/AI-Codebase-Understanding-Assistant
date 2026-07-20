from __future__ import annotations

from dataclasses import dataclass
import hashlib
from math import ceil

from app.schemas.api import EvidenceDTO
from app.services.evidence.selection import ValidatedEvidenceBlock
from app.services.index_models import FileRecord, RepositoryState
from app.services.text_utils import read_text


PROVIDER_BLOCK_OVERHEAD_TOKENS = 32
PROVIDER_CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class ProviderEvidenceBlock:
    """A validated whole source span that may cross the provider boundary."""

    evidence_id: str
    repository_id: str
    index_version_id: str
    file_path: str
    start_line: int
    end_line: int
    symbol_name: str | None
    support_type: str
    content: str
    token_estimate: int

    def __post_init__(self) -> None:
        if (
            not self.evidence_id
            or not self.repository_id
            or not self.index_version_id
            or not self.file_path
            or self.start_line < 1
            or self.end_line < self.start_line
            or not self.support_type
            or not self.content.strip()
            or self.token_estimate <= 0
        ):
            raise ValueError("invalid provider evidence block")


@dataclass(frozen=True)
class ProviderEvidenceContext:
    """Complete all-or-nothing evidence context for one provider request."""

    repository_id: str
    index_version_id: str
    blocks: tuple[ProviderEvidenceBlock, ...]
    token_budget: int
    used_tokens: int

    def __post_init__(self) -> None:
        if not self.repository_id or not self.index_version_id or self.token_budget <= 0:
            raise ValueError("invalid provider evidence context")
        if not self.blocks or self.used_tokens <= 0 or self.used_tokens > self.token_budget:
            raise ValueError("provider evidence context is empty or over budget")
        if self.used_tokens != sum(block.token_estimate for block in self.blocks):
            raise ValueError("provider evidence token accounting mismatch")
        if len({block.evidence_id for block in self.blocks}) != len(self.blocks):
            raise ValueError("provider evidence ids must be unique")
        if any(
            block.repository_id != self.repository_id
            or block.index_version_id != self.index_version_id
            for block in self.blocks
        ):
            raise ValueError("provider evidence ownership mismatch")


class ProviderEvidenceContextBuilder:
    """Projects only current, source-backed evidence into provider-safe context."""

    def from_selected(
        self,
        repository: RepositoryState,
        selected: tuple[ValidatedEvidenceBlock, ...],
        token_budget: int,
    ) -> ProviderEvidenceContext | None:
        expected_index = self._index_version_id(repository)
        blocks: list[ProviderEvidenceBlock] = []
        for item in selected:
            if item.repository_id != repository.id or item.index_version_id != expected_index:
                return None
            source = self._validated_source_range(
                repository,
                item.file_path,
                item.start_line,
                item.end_line,
                expected_source_hash=item.source_sha256,
            )
            if source is None or source.strip() != item.content.strip():
                return None
            blocks.append(
                ProviderEvidenceBlock(
                    evidence_id=item.evidence_id,
                    repository_id=repository.id,
                    index_version_id=expected_index,
                    file_path=item.file_path,
                    start_line=item.start_line,
                    end_line=item.end_line,
                    symbol_name=item.symbol_name,
                    support_type=item.support_type.value,
                    content=item.content,
                    token_estimate=item.token_estimate,
                )
            )
        return self._complete_context(repository, expected_index, blocks, token_budget)

    def from_saved(
        self,
        repository: RepositoryState,
        evidences: list[EvidenceDTO],
        token_budget: int,
    ) -> ProviderEvidenceContext | None:
        expected_index = self._index_version_id(repository)
        blocks: list[ProviderEvidenceBlock] = []
        for evidence in evidences:
            metadata_index = evidence.metadata.get("index_version_id")
            if (
                evidence.repository_id != repository.id
                or evidence.index_version != repository.current_index_version
                or evidence.is_stale
                or (metadata_index is not None and metadata_index != expected_index)
            ):
                return None
            source = self._validated_source_range(
                repository,
                evidence.file_path,
                evidence.start_line,
                evidence.end_line,
                expected_source_hash=evidence.metadata.get("source_sha256"),
            )
            if source is None:
                return None
            token_estimate = PROVIDER_BLOCK_OVERHEAD_TOKENS + ceil(
                len(source) / PROVIDER_CHARS_PER_TOKEN
            )
            blocks.append(
                ProviderEvidenceBlock(
                    evidence_id=evidence.evidence_id,
                    repository_id=repository.id,
                    index_version_id=expected_index,
                    file_path=evidence.file_path,
                    start_line=evidence.start_line,
                    end_line=evidence.end_line,
                    symbol_name=evidence.symbol_name,
                    support_type=evidence.metadata.get("support_type", "source_exact"),
                    content=source,
                    token_estimate=token_estimate,
                )
            )
        return self._complete_context(repository, expected_index, blocks, token_budget)

    @staticmethod
    def _complete_context(
        repository: RepositoryState,
        index_version_id: str,
        blocks: list[ProviderEvidenceBlock],
        token_budget: int,
    ) -> ProviderEvidenceContext | None:
        if not blocks or token_budget <= 0:
            return None
        used_tokens = sum(block.token_estimate for block in blocks)
        if used_tokens > token_budget or len({block.evidence_id for block in blocks}) != len(blocks):
            return None
        return ProviderEvidenceContext(
            repository_id=repository.id,
            index_version_id=index_version_id,
            blocks=tuple(blocks),
            token_budget=token_budget,
            used_tokens=used_tokens,
        )

    def _validated_source_range(
        self,
        repository: RepositoryState,
        file_path: str,
        start_line: int,
        end_line: int,
        *,
        expected_source_hash: str | None = None,
    ) -> str | None:
        if file_path in self._blocked_paths(repository):
            return None
        file_record = self._file_record(repository, file_path)
        if file_record is None or not file_record.absolute_path.is_file():
            return None
        try:
            source_bytes = file_record.absolute_path.read_bytes()
            source_text = read_text(file_record.absolute_path)
        except OSError:
            return None
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        if source_hash != file_record.content_hash:
            return None
        if expected_source_hash is not None and source_hash != expected_source_hash:
            return None
        lines = source_text.splitlines()
        if start_line < 1 or end_line < start_line or end_line > len(lines):
            return None
        return "\n".join(lines[start_line - 1 : end_line])

    @staticmethod
    def _file_record(repository: RepositoryState, file_path: str) -> FileRecord | None:
        return next((item for item in repository.files if item.path == file_path), None)

    @staticmethod
    def _blocked_paths(repository: RepositoryState) -> set[str]:
        blocked: set[str] = set()
        records = [
            *repository.skipped_file_records,
            *getattr(repository, "security_warning_records", []),
        ]
        for record in records:
            value = record.get("file_path") or record.get("path")
            if isinstance(value, str) and value:
                blocked.add(value)
        return blocked

    @staticmethod
    def _index_version_id(repository: RepositoryState) -> str:
        return f"idx_compat_{max(repository.current_index_version, 0)}"
