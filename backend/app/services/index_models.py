from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO


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
    status: str = "created"
    files: list[FileRecord] = field(default_factory=list)
    symbols: list[SymbolRecord] = field(default_factory=list)
    endpoints: list[EndpointRecord] = field(default_factory=list)
    chunks: list[ChunkRecord] = field(default_factory=list)
    graph_nodes: list[GraphNodeDTO] = field(default_factory=list)
    graph_edges: list[GraphEdgeDTO] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failed_files: int = 0
    current_step: str = "created"
    started_at: str | None = None
    finished_at: str | None = None
