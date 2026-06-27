from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.api import (
    ChatRequest,
    ChatResponse,
    EvidenceDTO,
    FileContentResponse,
    FileTreeNodeDTO,
    GraphResponse,
    IndexRequest,
    IndexResponse,
    IndexStatusResponse,
    OverviewResponse,
    RepositoryCreateResponse,
    RepositoryDeleteResponse,
    RepositoryDTO,
    RepositoryImportRequest,
    SearchResponse,
)
from app.services.codebase_service import codebase_service

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=list[RepositoryDTO])
def list_repositories() -> list[RepositoryDTO]:
    return codebase_service.list_repositories()


@router.delete("/{repository_id}", response_model=RepositoryDeleteResponse)
def delete_repository(repository_id: str) -> RepositoryDeleteResponse:
    return codebase_service.delete_repository(repository_id)


@router.post("/import-local", response_model=RepositoryCreateResponse)
def import_local_repository(request: RepositoryImportRequest) -> RepositoryCreateResponse:
    return codebase_service.import_local(request.name, request.local_path)


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
    result = codebase_service.start_indexing(repository_id, request.force_reindex if request else False)
    return IndexResponse(**result)


@router.get("/{repository_id}/index/status", response_model=IndexStatusResponse)
def get_index_status(repository_id: str) -> IndexStatusResponse:
    return codebase_service.get_index_status(repository_id)


@router.get("/{repository_id}/overview", response_model=OverviewResponse)
def get_overview(repository_id: str) -> OverviewResponse:
    return codebase_service.get_overview(repository_id)


@router.post("/{repository_id}/chat", response_model=ChatResponse)
def chat_with_repository(repository_id: str, request: ChatRequest) -> ChatResponse:
    return codebase_service.chat(repository_id, request.message, request.conversation_id)


@router.get("/{repository_id}/evidence/{evidence_id}", response_model=EvidenceDTO)
def get_evidence(repository_id: str, evidence_id: str) -> EvidenceDTO:
    return codebase_service.get_evidence(repository_id, evidence_id)


@router.get("/{repository_id}/graph", response_model=GraphResponse)
def get_graph(repository_id: str) -> GraphResponse:
    return codebase_service.get_graph(repository_id)


@router.get("/{repository_id}/search", response_model=SearchResponse)
def search(repository_id: str, q: str) -> SearchResponse:
    return codebase_service.search(repository_id, q)


@router.get("/{repository_id}/files/tree", response_model=list[FileTreeNodeDTO])
def get_file_tree(repository_id: str) -> list[FileTreeNodeDTO]:
    return codebase_service.get_file_tree(repository_id)


@router.get("/{repository_id}/files/content", response_model=FileContentResponse)
def get_file_content(repository_id: str, path: str) -> FileContentResponse:
    return codebase_service.get_file_content(repository_id, path)
