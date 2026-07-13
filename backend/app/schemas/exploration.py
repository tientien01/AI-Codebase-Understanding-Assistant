from __future__ import annotations

from pydantic import BaseModel, Field


class ImportantFileDTO(BaseModel):
    file_path: str
    reason: str


class ModuleDTO(BaseModel):
    name: str
    summary: str
    file_count: int = 0


class EndpointDTO(BaseModel):
    method: str
    path: str
    handler: str
    file_path: str
    start_line: int
    end_line: int
    metadata: dict[str, str] = Field(default_factory=dict)


class OverviewResponse(BaseModel):
    repository_id: str
    name: str
    detected_stack: list[str]
    important_files: list[ImportantFileDTO]
    modules: list[ModuleDTO]
    endpoints: list[EndpointDTO]
    documentation_gaps: list[str]
    stats: dict[str, int]


class ReadingPathSignalDTO(BaseModel):
    type: str
    detail: str
    line: int | None = None


class ReadingPathItemDTO(BaseModel):
    rank: int
    file_path: str
    title: str
    reason: str
    confidence: str
    signals: list[ReadingPathSignalDTO] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ReadingPathResponse(BaseModel):
    repository_id: str
    index_version: int = 0
    items: list[ReadingPathItemDTO]


class SymbolDTO(BaseModel):
    symbol_id: str
    file_path: str
    symbol_type: str
    name: str
    start_line: int
    end_line: int
    signature: str = ""
    index_version: int = 0


class SymbolListResponse(BaseModel):
    items: list[SymbolDTO]
    next_cursor: str | None = None


class EndpointListResponse(BaseModel):
    items: list[EndpointDTO]
    next_cursor: str | None = None
