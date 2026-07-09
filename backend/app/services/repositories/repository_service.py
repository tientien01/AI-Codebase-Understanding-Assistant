from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import settings
from app.core.errors import DomainError
from app.schemas.api import (
    EndpointDTO,
    EndpointListResponse,
    ImportantFileDTO,
    ModuleDTO,
    OverviewResponse,
    ReadingPathItemDTO,
    ReadingPathResponse,
    ReadingPathSignalDTO,
    RepositoryBulkDeleteResponse,
    RepositoryCreateResponse,
    RepositoryDeleteResponse,
    RepositoryDTO,
    SymbolDTO,
    SymbolListResponse,
)
from app.services.index_models import RepositoryState
from app.services.language_registry import LANGUAGE_DEFINITIONS
from app.services.repositories.repository_store import RepositoryStore
from app.services.text_utils import read_text


class RepositoryService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store
        self.repositories: dict[str, RepositoryState] = {
            repository.id: repository for repository in self.store.list_repositories()
        }

    def list_repositories(self) -> list[RepositoryDTO]:
        return [self.repository_dto(repository) for repository in self.repositories.values()]

    def create_repository(self, repository: RepositoryState) -> RepositoryCreateResponse:
        self.repositories[repository.id] = repository
        self.persist_repository(repository)
        return RepositoryCreateResponse(
            repository_id=repository.id,
            name=repository.name,
            status=repository.status,
            source_type=repository.source_type,
        )

    def delete_repository(self, repository_id: str, clear_evidence) -> RepositoryDeleteResponse:
        repository = self.get_repository(repository_id)
        self.store.delete_repository(repository_id)
        self.repositories.pop(repository_id, None)
        self._delete_managed_storage(repository)
        clear_evidence(repository_id)
        return RepositoryDeleteResponse(deleted=True, repository_id=repository_id)

    def delete_repositories(self, repository_ids: list[str], clear_evidence) -> RepositoryBulkDeleteResponse:
        deleted_ids: list[str] = []
        for repository_id in repository_ids:
            repository = self.repositories.get(repository_id)
            if repository is None:
                continue
            self.store.delete_repository(repository_id)
            self.repositories.pop(repository_id, None)
            self._delete_managed_storage(repository)
            clear_evidence(repository_id)
            deleted_ids.append(repository_id)
        return RepositoryBulkDeleteResponse(deleted_count=len(deleted_ids), repository_ids=deleted_ids)

    def persist_repository(self, repository: RepositoryState) -> None:
        self.store.save_repository(repository)

    def persist_repository_metadata(self, repository: RepositoryState) -> None:
        self.store.save_repository_metadata(repository)

    def replace_repository_index(self, repository: RepositoryState, indexed_repository: RepositoryState) -> None:
        repository.status = indexed_repository.status
        repository.current_index_version = indexed_repository.current_index_version
        repository.files = indexed_repository.files
        repository.symbols = indexed_repository.symbols
        repository.endpoints = indexed_repository.endpoints
        repository.chunks = indexed_repository.chunks
        repository.graph_nodes = indexed_repository.graph_nodes
        repository.graph_edges = indexed_repository.graph_edges
        repository.logs = indexed_repository.logs
        repository.warnings = indexed_repository.warnings
        repository.skipped_file_records = indexed_repository.skipped_file_records
        repository.failed_file_records = indexed_repository.failed_file_records
        repository.failed_files = indexed_repository.failed_files
        repository.current_step = indexed_repository.current_step
        repository.started_at = indexed_repository.started_at
        repository.finished_at = indexed_repository.finished_at

    def get_repository(self, repository_id: str) -> RepositoryState:
        repository = self.repositories.get(repository_id)
        if repository is None:
            raise DomainError("REPOSITORY_NOT_FOUND", "Repository not found.", 404, {"repository_id": repository_id})
        return repository

    def get_indexed_repository(self, repository_id: str) -> RepositoryState:
        repository = self.get_repository(repository_id)
        if repository.status not in {"indexed", "indexed_with_warnings"}:
            raise DomainError("REPOSITORY_NOT_INDEXED", "Repository has not been indexed yet.", 409, {"repository_id": repository_id})
        return repository

    def repository_dto(self, repository: RepositoryState) -> RepositoryDTO:
        return RepositoryDTO(
            id=repository.id,
            name=repository.name,
            source_type=repository.source_type,
            source_label=repository.source_label,
            source_uri=None,
            status=repository.status,
            current_index_version=repository.current_index_version,
            detected_stack=self.detect_stack(repository),
            total_files=len(repository.files),
            indexed_files=len(repository.files) if repository.status in {"indexed", "indexed_with_warnings"} else 0,
            symbols=len(repository.symbols),
            endpoints=len(repository.endpoints),
            chunks=len(repository.chunks),
            graph_nodes=len(repository.graph_nodes),
            last_indexed_at=repository.finished_at,
        )

    def important_files(self, repository: RepositoryState) -> list[ImportantFileDTO]:
        important: list[ImportantFileDTO] = []
        for file_record in repository.files:
            name = Path(file_record.path).name.lower()
            if name in {"main.py", "app.py"}:
                important.append(ImportantFileDTO(file_path=file_record.path, reason="Backend entrypoint candidate"))
            elif name.startswith("readme"):
                important.append(ImportantFileDTO(file_path=file_record.path, reason="Project documentation"))
            elif "router" in file_record.path.lower() or "routes" in file_record.path.lower():
                important.append(ImportantFileDTO(file_path=file_record.path, reason="API routing file"))
        return important[:8]

    def build_modules(self, repository: RepositoryState) -> list[ModuleDTO]:
        counts: dict[str, int] = {}
        for file_record in repository.files:
            parts = file_record.path.split("/")
            module_name = parts[-2] if len(parts) > 1 else "root"
            counts[module_name] = counts.get(module_name, 0) + 1
        return [
            ModuleDTO(name=name, summary=f"{count} indexed files in this module.", file_count=count)
            for name, count in sorted(counts.items())[:8]
        ]

    def detect_stack(self, repository: RepositoryState) -> list[str]:
        stack: set[str] = set()
        display_by_language = {
            definition.language: definition.display_name
            for definition in LANGUAGE_DEFINITIONS
            if definition.language != "config"
        }
        for file in repository.files:
            display_name = display_by_language.get(file.language)
            if display_name:
                stack.add(display_name)
        if any(file.language == "python" and self._file_contains(file.absolute_path, "fastapi") for file in repository.files):
            stack.add("FastAPI")
        if any(Path(file.path).suffix.lower() in {".tsx", ".jsx"} for file in repository.files):
            stack.add("React")
        if repository.endpoints:
            stack.add("FastAPI")
        return sorted(stack)

    def documentation_gaps(self, repository: RepositoryState) -> list[str]:
        has_readme = any(Path(file.path).name.lower().startswith("readme") for file in repository.files)
        gaps = []
        if not has_readme:
            gaps.append("Repository has no README indexed.")
        if not any("test" in file.path.lower() for file in repository.files):
            gaps.append("No test files were detected.")
        if not repository.endpoints:
            gaps.append("No FastAPI endpoint was detected.")
        return gaps or ["No major documentation gap detected by MVP rules."]

    def get_overview(self, repository_id: str) -> OverviewResponse:
        repository = self.get_indexed_repository(repository_id)
        return OverviewResponse(
            repository_id=repository.id,
            name=repository.name,
            detected_stack=self.detect_stack(repository),
            important_files=self.important_files(repository),
            modules=self.build_modules(repository),
            endpoints=[
                EndpointDTO(
                    method=endpoint.method,
                    path=endpoint.path,
                    handler=endpoint.handler,
                    file_path=endpoint.file_path,
                    start_line=endpoint.start_line,
                    end_line=endpoint.end_line,
                    metadata=endpoint.metadata,
                )
                for endpoint in repository.endpoints
            ],
            documentation_gaps=self.documentation_gaps(repository),
            stats={
                "files": len(repository.files),
                "functions": len([symbol for symbol in repository.symbols if symbol.symbol_type in {"function", "method"}]),
                "classes": len([symbol for symbol in repository.symbols if symbol.symbol_type == "class"]),
                "endpoints": len(repository.endpoints),
                "chunks": len(repository.chunks),
                "graph_nodes": len(repository.graph_nodes),
            },
        )

    def get_reading_path(self, repository_id: str) -> ReadingPathResponse:
        repository = self.get_indexed_repository(repository_id)
        items: list[ReadingPathItemDTO] = []
        for file in self.important_files(repository)[:7]:
            signals = [ReadingPathSignalDTO(type="heuristic", detail=file.reason)]
            if Path(file.file_path).name.lower().startswith("readme"):
                title = "Project documentation"
                confidence = "high"
            elif Path(file.file_path).name.lower() in {"main.py", "app.py"}:
                title = "Application entrypoint"
                confidence = "high"
            elif "router" in file.file_path.lower() or "routes" in file.file_path.lower():
                title = "API routing file"
                confidence = "medium"
            else:
                title = "Important file"
                confidence = "medium"
            items.append(
                ReadingPathItemDTO(
                    rank=len(items) + 1,
                    file_path=file.file_path,
                    title=title,
                    reason=file.reason,
                    confidence=confidence,
                    signals=signals,
                )
            )
        return ReadingPathResponse(repository_id=repository.id, index_version=repository.current_index_version, items=items)

    def list_symbols(self, repository_id: str, query: str | None = None, symbol_type: str | None = None) -> SymbolListResponse:
        repository = self.get_indexed_repository(repository_id)
        normalized_query = (query or "").lower()
        items = []
        for symbol in repository.symbols:
            if normalized_query and normalized_query not in symbol.name.lower() and normalized_query not in symbol.file_path.lower():
                continue
            if symbol_type and symbol.symbol_type != symbol_type:
                continue
            items.append(
                SymbolDTO(
                    symbol_id=symbol.id,
                    file_path=symbol.file_path,
                    symbol_type=symbol.symbol_type,
                    name=symbol.name,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    signature=symbol.signature,
                    index_version=repository.current_index_version,
                )
            )
        return SymbolListResponse(items=items[:100])

    def list_endpoints(self, repository_id: str) -> EndpointListResponse:
        repository = self.get_indexed_repository(repository_id)
        return EndpointListResponse(
            items=[
                EndpointDTO(
                    method=endpoint.method,
                    path=endpoint.path,
                    handler=endpoint.handler,
                    file_path=endpoint.file_path,
                    start_line=endpoint.start_line,
                    end_line=endpoint.end_line,
                    metadata=endpoint.metadata,
                )
                for endpoint in repository.endpoints
            ]
        )

    def _delete_managed_storage(self, repository: RepositoryState) -> None:
        repository_root = (settings.repository_storage_dir / repository.id).resolve()
        storage_root = settings.repository_storage_dir.resolve()
        if repository_root.exists() and self._is_relative_to(repository_root, storage_root):
            shutil.rmtree(repository_root)

        if repository.source_type == "upload_zip" and repository.source_uri:
            upload_path = Path(repository.source_uri).resolve()
            upload_root = settings.upload_storage_dir.resolve()
            if upload_path.exists() and upload_path.is_file() and self._is_relative_to(upload_path, upload_root):
                upload_path.unlink()

    def _file_contains(self, path: Path, value: str) -> bool:
        try:
            return value in read_text(path).lower()
        except OSError:
            return False

    def _is_relative_to(self, path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
        except ValueError:
            return False
        return True
