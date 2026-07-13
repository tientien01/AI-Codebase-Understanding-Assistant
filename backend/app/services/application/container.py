from __future__ import annotations

from app.services.application.use_cases import (
    AssistantUseCases,
    ExplorationUseCases,
    GraphUseCases,
    IndexingUseCases,
    RepositoryUseCases,
    SearchUseCases,
)
from app.services.artifacts.store import FilesystemArtifactStore
from app.services.chat.chat_service import ChatService
from app.services.chunking_service import ChunkingService
from app.services.evidence.evidence_service import EvidenceService
from app.services.files.file_service import FileService
from app.services.graph.graph_projection_service import GraphProjectionService
from app.services.graph.graph_service import GraphService
from app.services.impact.impact_analysis_service import ImpactAnalysisService
from app.services.indexing.indexing_job_service import IndexingJobService
from app.services.indexing.indexing_service import IndexingService
from app.services.indexing.job_queue import DramatiqIndexJobQueue, create_dramatiq_broker
from app.services.indexing.job_state_store import JobStateStore
from app.services.ingestion.archive_service import ArchiveService
from app.services.ingestion.import_session_service import ImportSessionService
from app.services.ingestion.upload_service import UploadService
from app.services.parsing.parser_service import ParserService
from app.services.repositories.repository_service import RepositoryService
from app.services.repositories.repository_store import RepositoryStore
from app.services.repositories.production_repository_store import ProductionRepositoryStore
from app.core.config import settings
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.search_service import SearchService
from app.services.scanning.scanner_service import ScannerService
from app.services.settings.settings_service import SettingsService


def create_repository_store():
    """Select persistence only at the composition root."""

    return ProductionRepositoryStore() if settings.app_env == "production" else RepositoryStore()


def create_index_job_queue():
    """Keep Redis optional locally and select it only for production dispatch."""

    if settings.app_env != "production":
        return None
    return DramatiqIndexJobQueue(create_dramatiq_broker(settings.redis_url))


def create_artifact_store():
    """Select the accepted filesystem artifact adapter at composition."""

    return FilesystemArtifactStore(settings.artifact_root)


class ApplicationContainer:
    """Composition root for the current single-process application profile."""

    def __init__(self) -> None:
        self.store = create_repository_store()
        self.artifact_store = create_artifact_store()
        self.index_job_queue = create_index_job_queue()
        self.job_state_store = (
            JobStateStore(self.store.engine)
            if isinstance(self.store, ProductionRepositoryStore)
            else None
        )
        self.chunking = ChunkingService()
        self.scanner = ScannerService()
        self.parser = ParserService(self.chunking)
        self.graph = GraphService()
        self.graph_projection = GraphProjectionService()
        self.impact = ImpactAnalysisService()
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
            self.index_job_queue,
            self.job_state_store,
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

        self.repository_use_cases = RepositoryUseCases(self.repositories_service, self.ingestion, self.evidence)
        self.indexing_use_cases = IndexingUseCases(self.indexing, self.indexing_jobs)
        self.exploration_use_cases = ExplorationUseCases(self.repositories_service)
        self.assistant_use_cases = AssistantUseCases(self.repositories_service, self.chat_service, self.evidence)
        self.graph_use_cases = GraphUseCases(
            self.repositories_service,
            self.graph,
            self.graph_projection,
            self.indexing,
            self.impact,
        )
        self.search_use_cases = SearchUseCases(self.search_service, self.file_service)
