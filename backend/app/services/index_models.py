from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO, ImportPreviewResponse
from app.services.code_analysis.models import ResolvedReference


@dataclass
class IndexingJobRecord:
    id: str
    repository_id: str
    status: str
    index_version: int = 0
    current_step: str = "queued"
    total_files: int = 0
    processed_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    total_graph_nodes: int = 0
    total_graph_edges: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_file_records: list[dict[str, str | None]] = field(default_factory=list)
    failed_file_records: list[dict[str, str | int | None]] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class ImportSessionRecord:
    id: str
    name: str
    source_type: str
    source_uri: str | None
    source_path: Path
    source_label: str | None = None
    status: str = "created"
    created_at: str | None = None
    confirmed_repository_id: str | None = None
    skipped_file_records: list[dict[str, str | None]] = field(default_factory=list)
    security_warning_records: list[dict[str, str]] = field(default_factory=list)
    activity_logs: list[dict[str, str | dict[str, str]]] = field(default_factory=list)
    preview_response: ImportPreviewResponse | None = None
    preview_project_fingerprint: str | None = None


@dataclass
class FileRecord:
    path: str
    absolute_path: Path
    language: str
    file_type: str
    size_bytes: int
    content_hash: str
    parse_status: str = "parsed"


@dataclass
class SymbolRecord:
    id: str
    name: str
    symbol_type: str
    file_path: str
    start_line: int
    end_line: int
    signature: str = ""


@dataclass
class EndpointRecord:
    method: str
    path: str
    handler: str
    file_path: str
    start_line: int
    end_line: int
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ChunkRecord:
    id: str
    file_path: str
    chunk_type: str
    content: str
    start_line: int
    end_line: int
    symbol_name: str | None = None
    score: float = 0.0
    content_hash: str = ""


@dataclass
class RepositoryState:
    id: str
    name: str
    source_type: str
    source_uri: str | None
    source_path: Path
    source_label: str | None = None
    status: str = "created"
    current_index_version: int = 0
    project_fingerprint: str | None = None
    files: list[FileRecord] = field(default_factory=list)
    symbols: list[SymbolRecord] = field(default_factory=list)
    endpoints: list[EndpointRecord] = field(default_factory=list)
    chunks: list[ChunkRecord] = field(default_factory=list)
    graph_nodes: list[GraphNodeDTO] = field(default_factory=list)
    graph_edges: list[GraphEdgeDTO] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_file_records: list[dict[str, str | None]] = field(default_factory=list)
    failed_file_records: list[dict[str, str | int | None]] = field(default_factory=list)
    parse_diagnostics: list[dict[str, str | int | None]] = field(default_factory=list)
    resolved_references: list[ResolvedReference] = field(default_factory=list)
    failed_files: int = 0
    current_step: str = "created"
    started_at: str | None = None
    finished_at: str | None = None
