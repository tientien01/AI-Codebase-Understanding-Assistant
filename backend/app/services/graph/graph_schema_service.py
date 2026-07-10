from __future__ import annotations

from pathlib import Path

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO
from app.services.index_models import RepositoryState


CANONICAL_NODE_TYPES = {
    "folder",
    "file",
    "module",
    "class",
    "schema",
    "model",
    "function",
    "method",
    "component",
    "endpoint",
    "api_call",
    "call_site",
    "builtin_call",
    "stdlib_call",
    "framework_call",
    "external_call",
    "unresolved_call",
    "cfg_node",
    "dfg_node",
    "unknown",
}

CANONICAL_EDGE_TYPES = {
    "contains",
    "defines",
    "imports",
    "imports_internal",
    "calls",
    "calls_api",
    "contains_call",
    "exposes_endpoint",
    "calls_builtin",
    "calls_stdlib",
    "calls_framework",
    "calls_external",
    "calls_unresolved",
    "cfg_next",
    "cfg_true",
    "cfg_false",
    "cfg_return",
    "dfg_parameter",
    "dfg_defines",
    "dfg_uses",
    "dfg_computed_from",
    "dfg_returned",
    "uses_model",
    "uses_schema",
    "reads_config",
    "tested_by",
    "documents",
    "related_to",
}

VALID_COVERAGE = {"mapped", "analyzing", "deep_indexed", "skipped", "failed"}
VALID_EVIDENCE_LEVELS = {"map", "deep", "inferred"}


class GraphSchemaService:
    """Normalize graph records into the canonical contract used by storage, API, and UI."""

    def normalize_repository_graph(self, repository: RepositoryState) -> None:
        nodes_by_id: dict[str, GraphNodeDTO] = {}
        for node in repository.graph_nodes:
            normalized = self.normalize_node(node)
            existing = nodes_by_id.get(normalized.id)
            nodes_by_id[normalized.id] = self._merge_nodes(existing, normalized) if existing else normalized

        normalized_edges: list[GraphEdgeDTO] = []
        for edge in repository.graph_edges:
            if edge.source not in nodes_by_id or edge.target not in nodes_by_id:
                repository.parse_diagnostics.append(
                    {
                        "file_path": None,
                        "language": None,
                        "parser": "graph-schema",
                        "stage": "graph_normalization",
                        "severity": "warning",
                        "message": f"Dropped graph edge with missing endpoint: {edge.source} -[{edge.type}]-> {edge.target}",
                        "line": None,
                    }
                )
                continue
            normalized_edges.append(self.normalize_edge(edge))

        repository.graph_nodes = list(nodes_by_id.values())
        repository.graph_edges = normalized_edges

    def normalize_node(self, node: GraphNodeDTO) -> GraphNodeDTO:
        node_type = node.type if node.type in CANONICAL_NODE_TYPES else "unknown"
        file_path = node.file_path.replace("\\", "/") if node.file_path else None
        scope_path = (node.scope_path or file_path)
        if scope_path:
            scope_path = scope_path.replace("\\", "/")
        tags = self._normalize_tags([*node.tags, *self._inferred_tags(node_type, file_path, node.label)])
        metadata = dict(node.metadata)
        if node.type != node_type:
            metadata.setdefault("original_type", node.type)

        return GraphNodeDTO(
            id=node.id,
            type=node_type,
            label=node.label[:180],
            file_path=file_path,
            start_line=node.start_line,
            end_line=node.end_line,
            summary=node.summary or self._summary(node_type, node.label, file_path),
            tags=tags,
            complexity=node.complexity or self._complexity(node_type),
            layer=node.layer or self._layer(node_type, file_path),
            coverage=node.coverage if node.coverage in VALID_COVERAGE else "deep_indexed",
            scope_path=scope_path,
            role=node.role or self._role(node_type),
            metadata=metadata,
        )

    def normalize_edge(self, edge: GraphEdgeDTO) -> GraphEdgeDTO:
        edge_type = edge.type if edge.type in CANONICAL_EDGE_TYPES else "related_to"
        metadata = dict(edge.metadata)
        if edge.type != edge_type:
            metadata.setdefault("original_type", edge.type)
        confidence = self._clamp(edge.confidence, 0.0, 1.0)
        return GraphEdgeDTO(
            source=edge.source,
            target=edge.target,
            type=edge_type,
            confidence=confidence,
            evidence_level=edge.evidence_level if edge.evidence_level in VALID_EVIDENCE_LEVELS else "inferred",
            weight=edge.weight if edge.weight is not None else round(confidence, 4),
            metadata=metadata,
        )

    def _merge_nodes(self, existing: GraphNodeDTO, incoming: GraphNodeDTO) -> GraphNodeDTO:
        return GraphNodeDTO(
            id=existing.id,
            type=existing.type if existing.type != "unknown" else incoming.type,
            label=existing.label or incoming.label,
            file_path=existing.file_path or incoming.file_path,
            start_line=existing.start_line or incoming.start_line,
            end_line=existing.end_line or incoming.end_line,
            summary=existing.summary or incoming.summary,
            tags=self._normalize_tags([*existing.tags, *incoming.tags]),
            complexity=existing.complexity or incoming.complexity,
            layer=existing.layer or incoming.layer,
            coverage=existing.coverage if existing.coverage != "mapped" else incoming.coverage,
            scope_path=existing.scope_path or incoming.scope_path,
            role=existing.role or incoming.role,
            metadata={**incoming.metadata, **existing.metadata},
        )

    def _summary(self, node_type: str, label: str, file_path: str | None) -> str:
        if node_type == "file" and file_path:
            return f"Source file {file_path}."
        if node_type == "folder":
            return f"Project folder {label}."
        if node_type == "endpoint":
            return f"API endpoint {label}."
        if node_type in {"function", "method", "class", "schema", "model", "component"}:
            return f"{node_type.replace('_', ' ').title()} {label}."
        return f"{node_type.replace('_', ' ').title()} {label}."

    def _role(self, node_type: str) -> str:
        return {
            "folder": "Project area",
            "file": "Source file",
            "module": "Import target",
            "endpoint": "API endpoint",
            "api_call": "Frontend or client API call",
            "cfg_node": "Control flow node",
            "dfg_node": "Data flow node",
        }.get(node_type, node_type.replace("_", " ").title())

    def _complexity(self, node_type: str) -> str:
        if node_type in {"cfg_node", "dfg_node", "unresolved_call"}:
            return "medium"
        if node_type in {"folder", "file", "module"}:
            return "low"
        return "unknown"

    def _layer(self, node_type: str, file_path: str | None) -> str:
        lower = (file_path or "").lower()
        path_parts = set(Path(lower).parts)
        if "frontend" in path_parts or "client" in path_parts or "ui" in path_parts:
            return "frontend"
        if "backend" in path_parts or "api" in path_parts or "server" in path_parts:
            return "backend"
        if "tests" in path_parts or "test" in lower:
            return "tests"
        if "docs" in path_parts or node_type == "folder" and "doc" in lower:
            return "documentation"
        if node_type == "endpoint":
            return "api"
        if node_type in {"module", "external_call", "framework_call", "stdlib_call", "builtin_call"}:
            return "external"
        return "application"

    def _inferred_tags(self, node_type: str, file_path: str | None, label: str) -> list[str]:
        tags = [node_type]
        lower = f"{file_path or ''} {label}".lower()
        for token in ("auth", "login", "config", "database", "api", "test"):
            if token in lower:
                tags.append(token)
        return tags

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for tag in tags:
            value = tag.strip().lower().replace(" ", "_")
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
