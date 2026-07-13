from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.assistant import CitationDTO


class SearchResultDTO(BaseModel):
    evidence_id: str
    file_path: str
    title: str
    preview: str
    start_line: int
    end_line: int
    score: float
    result_type: str = "chunk"
    retrieval_source: str = "hybrid"
    matched_terms: list[str] = Field(default_factory=list)
    index_version: int = 0
    is_stale: bool = False


class SearchResponse(BaseModel):
    results: list[SearchResultDTO]


class FileTreeNodeDTO(BaseModel):
    name: str
    path: str
    type: str
    children: list["FileTreeNodeDTO"] = Field(default_factory=list)


class FileContentResponse(BaseModel):
    file_path: str
    language: str
    content: str
    lines: list[str]
    symbols: list[CitationDTO] = Field(default_factory=list)
