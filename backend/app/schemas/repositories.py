from __future__ import annotations

from pydantic import BaseModel, Field


class RepositoryDTO(BaseModel):
    id: str
    name: str
    source_type: str
    source_label: str | None = None
    source_uri: str | None = None
    status: str
    current_index_version: int = 0
    detected_stack: list[str] = Field(default_factory=list)
    total_files: int = 0
    indexed_files: int = 0
    symbols: int = 0
    endpoints: int = 0
    chunks: int = 0
    graph_nodes: int = 0
    last_indexed_at: str | None = None


class RepositoryCreateResponse(BaseModel):
    repository_id: str
    name: str
    status: str
    source_type: str


class RepositoryDeleteResponse(BaseModel):
    deleted: bool
    repository_id: str


class RepositoryBulkDeleteRequest(BaseModel):
    repository_ids: list[str] = Field(default_factory=list)
    delete_all: bool = False


class RepositoryBulkDeleteResponse(BaseModel):
    deleted_count: int
    repository_ids: list[str] = Field(default_factory=list)
