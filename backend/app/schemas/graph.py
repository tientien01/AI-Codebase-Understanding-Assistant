from __future__ import annotations

from pydantic import BaseModel, Field


class GraphNodeDTO(BaseModel):
    id: str
    type: str
    label: str
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    complexity: str | None = None
    layer: str | None = None
    coverage: str = "deep_indexed"
    scope_path: str | None = None
    role: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class GraphEdgeDTO(BaseModel):
    source: str
    target: str
    type: str
    confidence: float
    evidence_level: str = "deep"
    weight: float | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: list[GraphNodeDTO]
    edges: list[GraphEdgeDTO]


class GraphExpansionRequest(BaseModel):
    scope_path: str


class GraphExpansionResponse(BaseModel):
    job_id: str | None = None
    status: str
    scope_path: str
    message: str


class ImpactAnalysisRequest(BaseModel):
    target_type: str
    target_ref: str
    max_depth: int = 2


class ImpactTargetDTO(BaseModel):
    node_id: str
    node_type: str
    label: str
    file_path: str | None = None
    line_range: str | None = None


class ImpactItemDTO(BaseModel):
    node_id: str
    node_type: str
    label: str
    file_path: str | None = None
    depth: int
    confidence: float
    via_edge: str | None = None
    reason: str


class ImpactAnalysisResponse(BaseModel):
    repository_id: str
    target: ImpactTargetDTO | None = None
    risk_level: str
    risk_score: int
    direct: list[ImpactItemDTO] = Field(default_factory=list)
    indirect: list[ImpactItemDTO] = Field(default_factory=list)
    affected_files: list[ImpactItemDTO] = Field(default_factory=list)
    affected_endpoints: list[ImpactItemDTO] = Field(default_factory=list)
    affected_tests: list[ImpactItemDTO] = Field(default_factory=list)
    affected_symbols: list[ImpactItemDTO] = Field(default_factory=list)
    suggested_checks: list[str] = Field(default_factory=list)
    missing_relations: list[str] = Field(default_factory=list)
