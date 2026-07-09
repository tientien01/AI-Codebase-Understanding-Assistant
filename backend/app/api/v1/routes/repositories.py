from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.api import (
    ChatRequest,
    ChatResponse,
    EndpointListResponse,
    EvidenceDTO,
    EvidenceValidationRequest,
    EvidenceValidationResponse,
    FailedFilesResponse,
    FileContentResponse,
    FileTreeNodeDTO,
    GraphExpansionRequest,
    GraphExpansionResponse,
    GraphResponse,
    GitHubImportRequest,
    IgnorePatternsResponse,
    ImportCancelResponse,
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
    ImportSessionCreateResponse,
    IndexJobControlResponse,
    IndexJobListResponse,
    IndexWarningsResponse,
    IndexRequest,
    IndexResponse,
    IndexStatusResponse,
    OverviewResponse,
    ReadingPathResponse,
    RepositoryBulkDeleteRequest,
    RepositoryBulkDeleteResponse,
    RepositoryCreateResponse,
    RepositoryDeleteResponse,
    RepositoryDTO,
    SearchAskWithEvidenceRequest,
    SearchResponse,
    SettingsResponse,
    SkippedFilesResponse,
    StalenessResponse,
    SymbolListResponse,
)
from app.services.codebase_service import codebase_service

router = APIRouter(prefix="/repositories", tags=["repositories"])
import_sessions_router = APIRouter(prefix="/import-sessions", tags=["import-sessions"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])


@import_sessions_router.post("/upload-zip", response_model=ImportSessionCreateResponse)
async def create_zip_import_session(file: UploadFile = File(...), name: str | None = Form(default=None)) -> ImportSessionCreateResponse:
    return await codebase_service.create_zip_import_session(file, name)


@import_sessions_router.post("/upload-folder", response_model=ImportSessionCreateResponse)
async def create_folder_import_session(
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    name: str | None = Form(default=None),
) -> ImportSessionCreateResponse:
    return await codebase_service.create_folder_import_session(files, relative_paths, name)


@import_sessions_router.post("/github", response_model=ImportSessionCreateResponse)
def create_github_import_session(request: GitHubImportRequest) -> ImportSessionCreateResponse:
    return codebase_service.create_github_import_session(request.url, request.name, request.branch)


@import_sessions_router.get("/{import_session_id}/preview", response_model=ImportPreviewResponse)
def get_import_preview(import_session_id: str) -> ImportPreviewResponse:
    return codebase_service.get_import_preview(import_session_id)


@import_sessions_router.post("/{import_session_id}/confirm", response_model=ImportConfirmResponse)
def confirm_import_session(import_session_id: str, request: ImportConfirmRequest) -> ImportConfirmResponse:
    return codebase_service.confirm_import_session(
        import_session_id,
        request.name,
        request.start_indexing,
        request.duplicate_action,
        run_in_background=True,
    )


@import_sessions_router.delete("/{import_session_id}", response_model=ImportCancelResponse)
def cancel_import_session(import_session_id: str) -> ImportCancelResponse:
    return codebase_service.cancel_import_session(import_session_id)


@router.get("", response_model=list[RepositoryDTO])
def list_repositories() -> list[RepositoryDTO]:
    return codebase_service.list_repositories()


@router.post("/bulk-delete", response_model=RepositoryBulkDeleteResponse)
def delete_repositories(request: RepositoryBulkDeleteRequest) -> RepositoryBulkDeleteResponse:
    return codebase_service.delete_repositories(request.repository_ids, request.delete_all)


@router.delete("/{repository_id}", response_model=RepositoryDeleteResponse)
def delete_repository(repository_id: str) -> RepositoryDeleteResponse:
    return codebase_service.delete_repository(repository_id)


@router.post("/upload", response_model=RepositoryCreateResponse)
async def upload_repository(file: UploadFile = File(...), name: str | None = Form(default=None)) -> RepositoryCreateResponse:
    return await codebase_service.upload_zip(file, name)


@router.post("/upload-folder", response_model=RepositoryCreateResponse)
async def upload_folder_repository(
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    name: str | None = Form(default=None),
) -> RepositoryCreateResponse:
    return await codebase_service.upload_folder(files, relative_paths, name)


@router.post("/{repository_id}/index", response_model=IndexResponse)
def start_indexing(repository_id: str, request: IndexRequest | None = None) -> IndexResponse:
    result = codebase_service.start_indexing_background(repository_id, request.force_reindex if request else False)
    return IndexResponse(**result)


@router.get("/{repository_id}/index/status", response_model=IndexStatusResponse)
def get_index_status(repository_id: str) -> IndexStatusResponse:
    return codebase_service.get_index_status(repository_id)


@router.get("/{repository_id}/index/jobs", response_model=IndexJobListResponse)
def list_indexing_jobs(repository_id: str) -> IndexJobListResponse:
    return codebase_service.list_indexing_jobs(repository_id)


@router.post("/{repository_id}/index/jobs/{job_id}/pause", response_model=IndexJobControlResponse)
def pause_indexing_job(repository_id: str, job_id: str) -> IndexJobControlResponse:
    result = codebase_service.pause_indexing_job(repository_id, job_id)
    return IndexJobControlResponse(**result)


@router.post("/{repository_id}/index/jobs/{job_id}/resume", response_model=IndexJobControlResponse)
def resume_indexing_job(repository_id: str, job_id: str) -> IndexJobControlResponse:
    result = codebase_service.resume_indexing_job(repository_id, job_id)
    return IndexJobControlResponse(**result)


@router.post("/{repository_id}/index/jobs/{job_id}/cancel", response_model=IndexJobControlResponse)
def cancel_indexing_job(repository_id: str, job_id: str) -> IndexJobControlResponse:
    result = codebase_service.cancel_indexing_job(repository_id, job_id)
    return IndexJobControlResponse(**result)


@router.get("/{repository_id}/index/jobs/{job_id}/warnings", response_model=IndexWarningsResponse)
def get_index_warnings(repository_id: str, job_id: str) -> IndexWarningsResponse:
    return codebase_service.get_index_warnings(repository_id, job_id)


@router.get("/{repository_id}/index/jobs/{job_id}/skipped-files", response_model=SkippedFilesResponse)
def get_skipped_files(repository_id: str, job_id: str) -> SkippedFilesResponse:
    return codebase_service.get_skipped_files(repository_id, job_id)


@router.get("/{repository_id}/index/jobs/{job_id}/failed-files", response_model=FailedFilesResponse)
def get_failed_files(repository_id: str, job_id: str) -> FailedFilesResponse:
    return codebase_service.get_failed_files(repository_id, job_id)


@router.get("/{repository_id}/staleness", response_model=StalenessResponse)
def get_staleness(repository_id: str) -> StalenessResponse:
    return codebase_service.get_staleness(repository_id)


@router.get("/{repository_id}/overview", response_model=OverviewResponse)
def get_overview(repository_id: str) -> OverviewResponse:
    return codebase_service.get_overview(repository_id)


@router.get("/{repository_id}/reading-path", response_model=ReadingPathResponse)
def get_reading_path(repository_id: str) -> ReadingPathResponse:
    return codebase_service.get_reading_path(repository_id)


@router.get("/{repository_id}/symbols", response_model=SymbolListResponse)
def list_symbols(repository_id: str, q: str | None = None, symbol_type: str | None = None) -> SymbolListResponse:
    return codebase_service.list_symbols(repository_id, q, symbol_type)


@router.get("/{repository_id}/api/endpoints", response_model=EndpointListResponse)
def list_endpoints(repository_id: str) -> EndpointListResponse:
    return codebase_service.list_endpoints(repository_id)


@router.post("/{repository_id}/chat", response_model=ChatResponse)
def chat_with_repository(repository_id: str, request: ChatRequest) -> ChatResponse:
    return codebase_service.chat(repository_id, request.message, request.conversation_id)


@router.get("/{repository_id}/evidence/{evidence_id}", response_model=EvidenceDTO)
def get_evidence(repository_id: str, evidence_id: str) -> EvidenceDTO:
    return codebase_service.get_evidence(repository_id, evidence_id)


@router.post("/{repository_id}/evidence/validate", response_model=EvidenceValidationResponse)
def validate_evidence(repository_id: str, request: EvidenceValidationRequest) -> EvidenceValidationResponse:
    return codebase_service.validate_evidence(repository_id, request.evidence_ids)


@router.get("/{repository_id}/graph", response_model=GraphResponse)
def get_graph(repository_id: str) -> GraphResponse:
    return codebase_service.get_graph(repository_id)


@router.get("/{repository_id}/graph/project-map", response_model=GraphResponse)
def get_project_map_graph(repository_id: str) -> GraphResponse:
    return codebase_service.get_project_map_graph(repository_id)


@router.get("/{repository_id}/graph/dependencies", response_model=GraphResponse)
def get_dependency_graph(repository_id: str, file_path: str | None = None) -> GraphResponse:
    return codebase_service.get_dependency_graph(repository_id, file_path)


@router.get("/{repository_id}/graph/api-flow", response_model=GraphResponse)
def get_api_flow_graph(repository_id: str, endpoint_id: str | None = None) -> GraphResponse:
    return codebase_service.get_api_flow_graph(repository_id, endpoint_id)


@router.get("/{repository_id}/graph/function-flow", response_model=GraphResponse)
def get_function_flow_graph(repository_id: str, symbol_id: str | None = None) -> GraphResponse:
    return codebase_service.get_function_flow_graph(repository_id, symbol_id)


@router.get("/{repository_id}/graph/data-flow", response_model=GraphResponse)
def get_data_flow_graph(repository_id: str, symbol_id: str | None = None) -> GraphResponse:
    return codebase_service.get_data_flow_graph(repository_id, symbol_id)


@router.post("/{repository_id}/graph/expand", response_model=GraphExpansionResponse)
def expand_graph_area(repository_id: str, request: GraphExpansionRequest) -> GraphExpansionResponse:
    return codebase_service.expand_graph_area(repository_id, request.scope_path)


@router.get("/{repository_id}/search", response_model=SearchResponse)
def search(repository_id: str, q: str) -> SearchResponse:
    return codebase_service.search(repository_id, q)


@router.post("/{repository_id}/search/ask-with-evidence", response_model=ChatResponse)
def ask_with_search_evidence(repository_id: str, request: SearchAskWithEvidenceRequest) -> ChatResponse:
    return codebase_service.ask_with_evidence(repository_id, request.message, request.evidence_ids, request.conversation_id)


@router.get("/{repository_id}/files/tree", response_model=list[FileTreeNodeDTO])
def get_file_tree(repository_id: str) -> list[FileTreeNodeDTO]:
    return codebase_service.get_file_tree(repository_id)


@router.get("/{repository_id}/files/content", response_model=FileContentResponse)
def get_file_content(repository_id: str, path: str) -> FileContentResponse:
    return codebase_service.get_file_content(repository_id, path)


@settings_router.get("", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    return codebase_service.get_settings()


@settings_router.get("/ignore-patterns", response_model=IgnorePatternsResponse)
def get_ignore_patterns() -> IgnorePatternsResponse:
    return codebase_service.get_ignore_patterns()
