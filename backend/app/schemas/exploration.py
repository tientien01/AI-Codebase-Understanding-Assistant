from __future__ import annotations

from typing import Literal

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


class ArchitectureEvidenceDTO(BaseModel):
    type: str
    detail: str
    file_path: str | None = None


class ArchitectureComponentDTO(BaseModel):
    id: str
    label: str
    kind: Literal["actor", "presentation", "container", "api", "application", "domain", "data_access", "messaging", "external_adapter", "entrypoint", "infrastructure", "module"]
    layer: str
    role: str | None = None
    support: Literal["confirmed", "inferred", "unknown"] = "inferred"
    summary: str
    technology: str | None = None
    parent_id: str | None = None
    file_paths: list[str] = Field(default_factory=list)
    endpoint_count: int = 0
    evidence: list[ArchitectureEvidenceDTO] = Field(default_factory=list)


class ArchitectureRelationDTO(BaseModel):
    source: str
    target: str
    label: str
    support: Literal["confirmed", "inferred", "unknown"]
    evidence: list[ArchitectureEvidenceDTO] = Field(default_factory=list)


class ArchitectureFlowStepDTO(BaseModel):
    component_id: str
    label: str
    support: Literal["confirmed", "inferred", "unknown"]


class ArchitectureFlowDTO(BaseModel):
    id: str
    label: str
    summary: str
    steps: list[ArchitectureFlowStepDTO] = Field(default_factory=list)
    evidence: list[ArchitectureEvidenceDTO] = Field(default_factory=list)


class ArchitectureOverviewDTO(BaseModel):
    style: Literal["layered_web", "backend_api", "mvc", "modular", "event_driven", "library", "cli", "package_map"] = "package_map"
    style_reason: str = "Architecture style was not classified."
    detector_version: str = "rule-based/v1"
    system_type: str
    summary: str
    technologies: list[str] = Field(default_factory=list)
    components: list[ArchitectureComponentDTO] = Field(default_factory=list)
    relations: list[ArchitectureRelationDTO] = Field(default_factory=list)
    primary_flows: list[ArchitectureFlowDTO] = Field(default_factory=list)
    coverage_state: Literal["ready", "limited"] = "limited"
    unknowns: list[str] = Field(default_factory=list)


class OverviewResponse(BaseModel):
    repository_id: str
    name: str
    detected_stack: list[str]
    important_files: list[ImportantFileDTO]
    modules: list[ModuleDTO]
    endpoints: list[EndpointDTO]
    documentation_gaps: list[str]
    stats: dict[str, int]
    architecture: ArchitectureOverviewDTO


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
