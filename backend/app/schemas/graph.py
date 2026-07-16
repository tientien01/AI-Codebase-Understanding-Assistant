from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


GRAPH_SEED_LIMIT_DEFAULT = 24
GRAPH_SEED_LIMIT_MAX = 100
GRAPH_NEIGHBOR_OFFSET_MAX = 100_000


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


class GraphProjectionRequest(BaseModel):
    index_version: int | None = Field(default=None, ge=1)
    root_keys: list[str] = Field(default_factory=list, max_length=20)
    node_types: list[str] = Field(default_factory=list, max_length=20)
    edge_types: list[str] = Field(default_factory=list, max_length=20)
    direction: Literal["outgoing", "incoming", "both"] = "both"
    max_depth: int = Field(default=2, ge=0, le=6)
    max_nodes: int = Field(default=220, ge=1, le=220)
    max_edges: int = Field(default=520, ge=0, le=520)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    support_levels: list[str] = Field(default_factory=list, max_length=10)
    projection_mode: Literal["full", "seeds", "neighbors"] = "full"
    dependency_scope: Literal["adaptive", "internal", "detected"] = "detected"
    seed_limit: int = Field(default=GRAPH_SEED_LIMIT_DEFAULT, ge=1, le=GRAPH_SEED_LIMIT_MAX)
    neighbor_offset: int = Field(default=0, ge=0, le=GRAPH_NEIGHBOR_OFFSET_MAX)

    @field_validator("root_keys", "node_types", "edge_types", "support_levels")
    @classmethod
    def normalize_filters(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip() for value in values if value.strip()})
        if any(len(value) > 200 for value in normalized):
            raise ValueError("Graph projection filters must be at most 200 characters")
        return normalized


class GraphProjectionCounts(BaseModel):
    available_nodes: int = 0
    included_nodes: int = 0
    available_edges: int = 0
    included_edges: int = 0
    available_counts_are_estimates: bool = False


class GraphProjectionCoverage(BaseModel):
    state: Literal["ready", "limited"] = "ready"
    measured: dict[str, int | float] = Field(default_factory=dict)
    unknown: list[str] = Field(default_factory=list)


class GraphProjectionTruncation(BaseModel):
    truncated: bool = False
    reason: str | None = None
    continuation_token: str | None = None


class GraphProjectionProvenance(BaseModel):
    source: str = "active_index_compatibility_graph"
    deterministic_order: bool = True
    support_levels: list[str] = Field(default_factory=list)


class GraphSeedDTO(BaseModel):
    node_id: str
    reason_codes: list[str] = Field(default_factory=list)
    incoming_available: int = 0
    outgoing_available: int = 0


class GraphNodeExpansionDTO(BaseModel):
    root_key: str
    incoming_available: int = 0
    outgoing_available: int = 0
    included_neighbors: int = 0
    remaining_neighbors: int = 0
    next_neighbor_offset: int | None = None
    leaf: bool = False
    limited: bool = False


class GraphResponse(BaseModel):
    nodes: list[GraphNodeDTO]
    edges: list[GraphEdgeDTO]
    repository_id: str | None = None
    index_version: int | None = None
    view: str = "all"
    projection: GraphProjectionRequest = Field(default_factory=GraphProjectionRequest)
    counts: GraphProjectionCounts = Field(default_factory=GraphProjectionCounts)
    coverage: GraphProjectionCoverage = Field(default_factory=GraphProjectionCoverage)
    truncation: GraphProjectionTruncation = Field(default_factory=GraphProjectionTruncation)
    unsupported_hops: list[str] = Field(default_factory=list)
    can_expand: bool = False
    provenance: GraphProjectionProvenance = Field(default_factory=GraphProjectionProvenance)
    dependency_scope_used: Literal["internal", "detected"] | None = None
    seed_strategy: str | None = None
    seeds: list[GraphSeedDTO] = Field(default_factory=list)
    additional_starting_points: int = 0
    expansion: GraphNodeExpansionDTO | None = None


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
