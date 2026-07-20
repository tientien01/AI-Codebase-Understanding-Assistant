from __future__ import annotations

from fastapi import UploadFile

from app.schemas.api import (
    AssistantRequestContext,
    ChatResponse,
    EndpointListResponse,
    EvidenceDTO,
    EvidenceValidationResponse,
    FailedFilesResponse,
    FileContentResponse,
    FileTreeNodeDTO,
    GraphExpansionResponse,
    GraphResponse,
    ImpactAnalysisResponse,
    IndexJobListResponse,
    IndexStatusResponse,
    IndexWarningsResponse,
    OverviewResponse,
    ReadingPathResponse,
    RepositoryBulkDeleteResponse,
    RepositoryCreateResponse,
    RepositoryDeleteResponse,
    RepositoryDTO,
    SearchResponse,
    SkippedFilesResponse,
    StalenessResponse,
    SymbolListResponse,
)
from app.services.chat.chat_service import ChatService
from app.services.evidence.evidence_service import EvidenceService
from app.services.files.file_service import FileService
from app.services.graph.graph_projection_service import GraphProjectionService
from app.schemas.graph import GraphProjectionRequest
from app.services.graph.graph_service import GraphService
from app.services.impact.impact_analysis_service import ImpactAnalysisService
from app.services.indexing.indexing_job_service import IndexingJobService
from app.services.indexing.indexing_service import IndexingService
from app.services.ingestion.import_session_service import ImportSessionService
from app.services.repositories.repository_service import RepositoryService
from app.services.retrieval.search_service import SearchService


class RepositoryUseCases:
    """Coordinates repository lifecycle operations exposed by the API."""

    def __init__(self, repositories: RepositoryService, ingestion: ImportSessionService, evidence: EvidenceService) -> None:
        self.repositories = repositories
        self.ingestion = ingestion
        self.evidence = evidence

    def list_repositories(self) -> list[RepositoryDTO]:
        return self.repositories.list_repositories()

    def delete_repository(self, repository_id: str) -> RepositoryDeleteResponse:
        return self.repositories.delete_repository(repository_id, self.evidence.clear_repository)

    def delete_repositories(self, repository_ids: list[str], delete_all: bool = False) -> RepositoryBulkDeleteResponse:
        target_ids = list(self.repositories.repositories) if delete_all else repository_ids
        return self.repositories.delete_repositories(target_ids, self.evidence.clear_repository)

    async def upload_zip(self, file: UploadFile, name: str | None) -> RepositoryCreateResponse:
        return await self.ingestion.upload_zip(file, name)

    async def upload_folder(
        self,
        files: list[UploadFile],
        relative_paths: list[str],
        name: str | None,
    ) -> RepositoryCreateResponse:
        return await self.ingestion.upload_folder(files, relative_paths, name)


class IndexingUseCases:
    """Coordinates index submission, control, and job observation."""

    def __init__(self, indexing: IndexingService, jobs: IndexingJobService) -> None:
        self.indexing = indexing
        self.jobs = jobs

    def start_indexing_background(self, repository_id: str, force_reindex: bool = False) -> dict[str, str | int]:
        return self.indexing.start_indexing_background(repository_id, force_reindex).model_dump()

    def get_index_status(self, repository_id: str) -> IndexStatusResponse:
        return self.indexing.get_index_status(repository_id)

    def list_indexing_jobs(self, repository_id: str) -> IndexJobListResponse:
        return self.jobs.list_indexing_jobs(repository_id)

    def pause_indexing_job(self, repository_id: str, job_id: str) -> dict[str, str | int]:
        return self.indexing.pause_indexing_job(repository_id, job_id).model_dump()

    def resume_indexing_job(self, repository_id: str, job_id: str) -> dict[str, str | int]:
        return self.indexing.resume_indexing_job(repository_id, job_id).model_dump()

    def cancel_indexing_job(self, repository_id: str, job_id: str) -> dict[str, str | int]:
        return self.indexing.cancel_indexing_job(repository_id, job_id).model_dump()

    def get_index_warnings(self, repository_id: str, job_id: str) -> IndexWarningsResponse:
        return self.jobs.get_index_warnings(repository_id, job_id)

    def get_skipped_files(self, repository_id: str, job_id: str) -> SkippedFilesResponse:
        return self.jobs.get_skipped_files(repository_id, job_id)

    def get_failed_files(self, repository_id: str, job_id: str) -> FailedFilesResponse:
        return self.jobs.get_failed_files(repository_id, job_id)

    def get_staleness(self, repository_id: str) -> StalenessResponse:
        return self.indexing.get_staleness(repository_id)


class ExplorationUseCases:
    """Exposes repository read models without leaking the repository service to routes."""

    def __init__(self, repositories: RepositoryService) -> None:
        self.repositories = repositories

    def get_overview(self, repository_id: str) -> OverviewResponse:
        return self.repositories.get_overview(repository_id)

    def get_reading_path(self, repository_id: str) -> ReadingPathResponse:
        return self.repositories.get_reading_path(repository_id)

    def list_symbols(self, repository_id: str, query: str | None = None, symbol_type: str | None = None) -> SymbolListResponse:
        return self.repositories.list_symbols(repository_id, query, symbol_type)

    def list_endpoints(self, repository_id: str) -> EndpointListResponse:
        return self.repositories.list_endpoints(repository_id)


class AssistantUseCases:
    """Coordinates assistant calls with evidence validation and repository lookup."""

    def __init__(self, repositories: RepositoryService, chat: ChatService, evidence: EvidenceService) -> None:
        self.repositories = repositories
        self.chat_service = chat
        self.evidence = evidence

    def chat(
        self,
        repository_id: str,
        message: str,
        conversation_id: str | None = None,
        context: AssistantRequestContext | None = None,
    ) -> ChatResponse:
        return self.chat_service.chat(repository_id, message, conversation_id, context)

    def get_evidence(self, repository_id: str, evidence_id: str) -> EvidenceDTO:
        return self.evidence.get_evidence(repository_id, evidence_id)

    def list_conversations(self, repository_id: str, limit: int):
        return self.chat_service.list_conversations(repository_id, limit)

    def get_conversation(self, repository_id: str, conversation_id: str, limit: int):
        return self.chat_service.get_conversation(repository_id, conversation_id, limit)

    def delete_conversation(self, repository_id: str, conversation_id: str) -> None:
        self.chat_service.delete_conversation(repository_id, conversation_id)

    def validate_evidence(self, repository_id: str, evidence_ids: list[str]) -> EvidenceValidationResponse:
        repository = self.repositories.get_repository(repository_id)
        return self.evidence.validate_evidence(repository, evidence_ids)

    def ask_with_evidence(
        self,
        repository_id: str,
        message: str,
        evidence_ids: list[str],
        conversation_id: str | None = None,
    ) -> ChatResponse:
        return self.chat_service.ask_with_evidence(repository_id, message, evidence_ids, conversation_id)


class GraphUseCases:
    """Coordinates graph projections, expansion, and impact analysis."""

    def __init__(
        self,
        repositories: RepositoryService,
        graph: GraphService,
        projection: GraphProjectionService,
        indexing: IndexingService,
        impact: ImpactAnalysisService,
    ) -> None:
        self.repositories = repositories
        self.graph = graph
        self.projection = projection
        self.indexing = indexing
        self.impact = impact

    def get_graph(self, repository_id: str, request: GraphProjectionRequest | None = None) -> GraphResponse:
        return self.graph.get_graph(self.repositories.get_indexed_repository(repository_id), request)

    def get_project_map_graph(self, repository_id: str, request: GraphProjectionRequest | None = None) -> GraphResponse:
        return self.projection.project_map(self.repositories.get_indexed_repository(repository_id), request)

    def get_dependency_graph(self, repository_id: str, file_path: str | None = None, request: GraphProjectionRequest | None = None) -> GraphResponse:
        return self.projection.dependencies(self.repositories.get_indexed_repository(repository_id), file_path, request)

    def get_api_flow_graph(self, repository_id: str, endpoint_id: str | None = None, request: GraphProjectionRequest | None = None) -> GraphResponse:
        return self.projection.api_flow(self.repositories.get_indexed_repository(repository_id), endpoint_id, request)

    def get_function_flow_graph(self, repository_id: str, symbol_id: str | None = None, request: GraphProjectionRequest | None = None) -> GraphResponse:
        return self.projection.function_flow(self.repositories.get_indexed_repository(repository_id), symbol_id, request)

    def get_data_flow_graph(self, repository_id: str, symbol_id: str | None = None, request: GraphProjectionRequest | None = None) -> GraphResponse:
        return self.projection.data_flow(self.repositories.get_indexed_repository(repository_id), symbol_id, request)

    def expand_graph_area(self, repository_id: str, scope_path: str) -> GraphExpansionResponse:
        result = self.indexing.start_indexing(repository_id, force_reindex=True)
        return GraphExpansionResponse(
            job_id=result.indexing_job_id,
            status=result.status,
            scope_path=scope_path,
            message="Detailed analysis was requested for this area. Current MVP refreshes the project graph while scoped indexing is being added.",
        )

    def analyze_impact(self, repository_id: str, target_type: str, target_ref: str, max_depth: int = 2) -> ImpactAnalysisResponse:
        repository = self.repositories.get_indexed_repository(repository_id)
        return self.impact.analyze(repository, target_type, target_ref, max_depth)


class SearchUseCases:
    """Coordinates search and bounded indexed-file reads."""

    def __init__(self, search: SearchService, files: FileService) -> None:
        self.search_service = search
        self.file_service = files

    def search(self, repository_id: str, query: str) -> SearchResponse:
        return self.search_service.search(repository_id, query)

    def get_file_tree(self, repository_id: str) -> list[FileTreeNodeDTO]:
        return self.file_service.get_file_tree(repository_id)

    def get_file_content(self, repository_id: str, file_path: str) -> FileContentResponse:
        return self.file_service.get_file_content(repository_id, file_path)
