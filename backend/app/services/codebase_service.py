from __future__ import annotations

from fastapi import UploadFile

from app.schemas.api import (
    ChatResponse,
    EndpointListResponse,
    EvidenceDTO,
    EvidenceValidationResponse,
    FailedFilesResponse,
    FileContentResponse,
    FileTreeNodeDTO,
    GraphResponse,
    IgnorePatternsResponse,
    ImportCancelResponse,
    ImportConfirmResponse,
    ImportPreviewResponse,
    ImportSessionCreateResponse,
    IndexJobListResponse,
    IndexStatusResponse,
    IndexWarningsResponse,
    OverviewResponse,
    ReadingPathResponse,
    RepositoryCreateResponse,
    RepositoryDeleteResponse,
    RepositoryDTO,
    SearchResponse,
    SettingsResponse,
    SkippedFilesResponse,
    StalenessResponse,
    SymbolListResponse,
)
from app.services.chat.chat_service import ChatService
from app.services.chunking_service import ChunkingService
from app.services.evidence.evidence_service import EvidenceService
from app.services.files.file_service import FileService
from app.services.graph.graph_service import GraphService
from app.services.indexing.indexing_job_service import IndexingJobService
from app.services.indexing.indexing_service import IndexingService
from app.services.ingestion.archive_service import ArchiveService
from app.services.ingestion.import_session_service import ImportSessionService
from app.services.ingestion.upload_service import UploadService
from app.services.parsing.parser_service import ParserService
from app.services.repositories.repository_service import RepositoryService
from app.services.repositories.repository_store import RepositoryStore
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.search_service import SearchService
from app.services.scanning.scanner_service import ScannerService
from app.services.settings.settings_service import SettingsService


class CodebaseService:
    """Backward-compatible facade over focused domain services."""

    def __init__(self) -> None:
        self.store = RepositoryStore()
        self.chunking = ChunkingService()
        self.scanner = ScannerService()
        self.parser = ParserService(self.chunking)
        self.graph = GraphService()
        self.retrieval = RetrievalService()
        self.archive = ArchiveService()
        self.upload = UploadService(self.archive)
        self.repositories_service = RepositoryService(self.store)
        self.evidence = EvidenceService(self.store)
        self.indexing = IndexingService(
            self.store,
            self.repositories_service,
            self.evidence,
            self.scanner,
            self.parser,
            self.chunking,
            self.graph,
        )
        self.indexing_jobs = IndexingJobService(self.store, self.repositories_service)
        self.ingestion = ImportSessionService(
            self.repositories_service,
            self.indexing,
            self.scanner,
            self.archive,
            self.upload,
        )
        self.search_service = SearchService(self.repositories_service, self.retrieval, self.evidence)
        self.chat_service = ChatService(self.repositories_service, self.retrieval, self.evidence)
        self.file_service = FileService(self.repositories_service)
        self.settings_service = SettingsService()

    @property
    def repositories(self):
        return self.repositories_service.repositories

    @property
    def import_sessions(self):
        return self.ingestion.import_sessions

    def list_repositories(self) -> list[RepositoryDTO]:
        return self.repositories_service.list_repositories()

    def delete_repository(self, repository_id: str) -> RepositoryDeleteResponse:
        return self.repositories_service.delete_repository(repository_id, self.evidence.clear_repository)

    async def upload_zip(self, file: UploadFile, name: str | None) -> RepositoryCreateResponse:
        return await self.ingestion.upload_zip(file, name)

    async def upload_folder(
        self,
        files: list[UploadFile],
        relative_paths: list[str],
        name: str | None,
    ) -> RepositoryCreateResponse:
        return await self.ingestion.upload_folder(files, relative_paths, name)

    async def create_zip_import_session(self, file: UploadFile, name: str | None) -> ImportSessionCreateResponse:
        return await self.ingestion.create_zip_import_session(file, name)

    async def create_folder_import_session(
        self,
        files: list[UploadFile],
        relative_paths: list[str],
        name: str | None,
    ) -> ImportSessionCreateResponse:
        return await self.ingestion.create_folder_import_session(files, relative_paths, name)

    def get_import_preview(self, import_session_id: str) -> ImportPreviewResponse:
        return self.ingestion.get_import_preview(import_session_id)

    def confirm_import_session(
        self,
        import_session_id: str,
        name: str | None,
        start_indexing: bool,
        duplicate_action: str = "import_as_new",
    ) -> ImportConfirmResponse:
        return self.ingestion.confirm_import_session(import_session_id, name, start_indexing, duplicate_action)

    def cancel_import_session(self, import_session_id: str) -> ImportCancelResponse:
        return self.ingestion.cancel_import_session(import_session_id)

    def start_indexing(self, repository_id: str, force_reindex: bool = False) -> dict[str, str | int]:
        response = self.indexing.start_indexing(repository_id, force_reindex)
        return response.model_dump()

    def get_index_status(self, repository_id: str) -> IndexStatusResponse:
        return self.indexing.get_index_status(repository_id)

    def list_indexing_jobs(self, repository_id: str) -> IndexJobListResponse:
        return self.indexing_jobs.list_indexing_jobs(repository_id)

    def get_index_warnings(self, repository_id: str, job_id: str) -> IndexWarningsResponse:
        return self.indexing_jobs.get_index_warnings(repository_id, job_id)

    def get_skipped_files(self, repository_id: str, job_id: str) -> SkippedFilesResponse:
        return self.indexing_jobs.get_skipped_files(repository_id, job_id)

    def get_failed_files(self, repository_id: str, job_id: str) -> FailedFilesResponse:
        return self.indexing_jobs.get_failed_files(repository_id, job_id)

    def get_staleness(self, repository_id: str) -> StalenessResponse:
        return self.indexing.get_staleness(repository_id)

    def get_overview(self, repository_id: str) -> OverviewResponse:
        return self.repositories_service.get_overview(repository_id)

    def get_reading_path(self, repository_id: str) -> ReadingPathResponse:
        return self.repositories_service.get_reading_path(repository_id)

    def list_symbols(self, repository_id: str, query: str | None = None, symbol_type: str | None = None) -> SymbolListResponse:
        return self.repositories_service.list_symbols(repository_id, query, symbol_type)

    def list_endpoints(self, repository_id: str) -> EndpointListResponse:
        return self.repositories_service.list_endpoints(repository_id)

    def chat(self, repository_id: str, message: str, conversation_id: str | None = None) -> ChatResponse:
        return self.chat_service.chat(repository_id, message, conversation_id)

    def get_evidence(self, repository_id: str, evidence_id: str) -> EvidenceDTO:
        return self.evidence.get_evidence(repository_id, evidence_id)

    def validate_evidence(self, repository_id: str, evidence_ids: list[str]) -> EvidenceValidationResponse:
        repository = self.repositories_service.get_repository(repository_id)
        return self.evidence.validate_evidence(repository, evidence_ids)

    def ask_with_evidence(
        self,
        repository_id: str,
        message: str,
        evidence_ids: list[str],
        conversation_id: str | None = None,
    ) -> ChatResponse:
        return self.chat_service.ask_with_evidence(repository_id, message, evidence_ids, conversation_id)

    def get_graph(self, repository_id: str) -> GraphResponse:
        repository = self.repositories_service.get_indexed_repository(repository_id)
        return self.graph.get_graph(repository)

    def get_file_tree(self, repository_id: str) -> list[FileTreeNodeDTO]:
        return self.file_service.get_file_tree(repository_id)

    def get_file_content(self, repository_id: str, file_path: str) -> FileContentResponse:
        return self.file_service.get_file_content(repository_id, file_path)

    def search(self, repository_id: str, query: str) -> SearchResponse:
        return self.search_service.search(repository_id, query)

    def get_settings(self) -> SettingsResponse:
        return self.settings_service.get_settings()

    def get_ignore_patterns(self) -> IgnorePatternsResponse:
        return self.settings_service.get_ignore_patterns()


codebase_service = CodebaseService()
