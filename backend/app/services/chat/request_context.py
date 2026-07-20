from __future__ import annotations

from dataclasses import dataclass
import hashlib

from app.schemas.assistant import AssistantRequestContext
from app.services.index_models import RepositoryState


class AssistantContextValidationError(ValueError):
    """Stable public-safe rejection for invalid workspace context."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ValidatedAssistantContext:
    page: str
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    symbol_name: str | None = None

    @property
    def retrieval_anchor(self) -> str:
        fields = [f"workspace-page:{self.page}"]
        if self.file_path:
            fields.append(f"workspace-file:{self.file_path}")
        if self.start_line is not None and self.end_line is not None:
            fields.append(f"workspace-lines:{self.start_line}-{self.end_line}")
        if self.symbol_name:
            fields.append(f"workspace-symbol:{self.symbol_name}")
        return " ".join(fields)


class AssistantRequestContextValidator:
    """Resolves client identifiers only against the current indexed repository."""

    def validate(
        self,
        repository: RepositoryState,
        context: AssistantRequestContext | None,
    ) -> ValidatedAssistantContext | None:
        if context is None:
            return None
        if context.page != "code":
            return ValidatedAssistantContext(page=context.page)

        file_record = next(
            (item for item in repository.files if item.path == context.file_path),
            None,
        )
        if file_record is None:
            raise AssistantContextValidationError("context_file_not_indexed")

        repository_root = repository.source_path.resolve()
        source_path = file_record.absolute_path.resolve()
        try:
            source_path.relative_to(repository_root)
        except ValueError as error:
            raise AssistantContextValidationError("context_file_outside_repository") from error
        if not source_path.is_file():
            raise AssistantContextValidationError("context_source_missing")

        source_bytes = source_path.read_bytes()
        if hashlib.sha256(source_bytes).hexdigest() != file_record.content_hash:
            raise AssistantContextValidationError("context_source_changed")
        line_count = max(
            1,
            source_bytes.count(b"\n") + (0 if source_bytes.endswith(b"\n") else 1),
        )
        if context.end_line is not None and context.end_line > line_count:
            raise AssistantContextValidationError("context_range_invalid")

        start_line = context.start_line
        end_line = context.end_line
        symbol_name = context.symbol_name
        if symbol_name is not None:
            symbol = next(
                (
                    item
                    for item in repository.symbols
                    if item.file_path == file_record.path and item.name == symbol_name
                ),
                None,
            )
            if symbol is None:
                raise AssistantContextValidationError("context_symbol_not_indexed")
            if start_line is None:
                start_line, end_line = symbol.start_line, symbol.end_line
            elif not (symbol.start_line <= start_line <= end_line <= symbol.end_line):
                raise AssistantContextValidationError("context_symbol_range_mismatch")

        return ValidatedAssistantContext(
            page=context.page,
            file_path=file_record.path,
            start_line=start_line,
            end_line=end_line,
            symbol_name=symbol_name,
        )
