from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO, ImpactAnalysisResponse, ImpactItemDTO, ImpactTargetDTO
from app.services.index_models import RepositoryState
from app.services.text_utils import node_id


SYMBOL_NODE_TYPES = {"function", "method", "class", "schema", "model", "component"}
TEST_PATH_MARKERS = {"/test/", "/tests/", "\\test\\", "\\tests\\"}
HIGH_RISK_EDGE_TYPES = {"calls", "calls_api", "exposes_endpoint", "imports_internal"}


@dataclass(frozen=True)
class TraversalHit:
    node: GraphNodeDTO
    depth: int
    confidence: float
    via_edge: GraphEdgeDTO | None
    path_edge_types: tuple[str, ...]


class ImpactAnalysisService:
    def analyze(self, repository: RepositoryState, target_type: str, target_ref: str, max_depth: int = 2) -> ImpactAnalysisResponse:
        bounded_depth = max(1, min(max_depth, 4))
        roots = self._resolve_targets(repository, target_type, target_ref)
        if not roots:
            return ImpactAnalysisResponse(
                repository_id=repository.id,
                risk_level="unknown",
                risk_score=0,
                missing_relations=[
                    f"Could not resolve {target_type} target '{target_ref}' to a graph node.",
                    "Try using an indexed file path, symbol name, symbol id, endpoint path, or endpoint label.",
                ],
            )

        root = roots[0]
        hits = self._traverse(repository, roots, bounded_depth)
        direct = [self._impact_item(hit) for hit in hits if hit.depth == 1]
        indirect = [self._impact_item(hit) for hit in hits if hit.depth > 1]
        affected_files = self._unique_items(
            [
                self._impact_item(hit)
                for hit in hits
                if hit.node.type == "file" or (hit.node.file_path and hit.node.file_path != root.file_path)
            ],
            key=lambda item: item.file_path or item.node_id,
        )
        affected_endpoints = self._unique_items(
            [self._impact_item(hit) for hit in hits if hit.node.type == "endpoint"],
            key=lambda item: item.node_id,
        )
        affected_tests = self._unique_items(
            [self._impact_item(hit) for hit in hits if self._is_test_node(hit.node)],
            key=lambda item: item.file_path or item.node_id,
        )
        affected_symbols = self._unique_items(
            [self._impact_item(hit) for hit in hits if hit.node.type in SYMBOL_NODE_TYPES],
            key=lambda item: item.node_id,
        )
        risk_score = self._risk_score(direct, indirect, affected_endpoints, affected_tests)
        return ImpactAnalysisResponse(
            repository_id=repository.id,
            target=self._target(root),
            risk_level=self._risk_level(risk_score),
            risk_score=risk_score,
            direct=direct[:20],
            indirect=indirect[:30],
            affected_files=affected_files[:20],
            affected_endpoints=affected_endpoints[:20],
            affected_tests=affected_tests[:20],
            affected_symbols=affected_symbols[:25],
            suggested_checks=self._suggested_checks(root, affected_endpoints, affected_tests, affected_files),
            missing_relations=self._missing_relations(repository, affected_tests),
        )

    def _resolve_targets(self, repository: RepositoryState, target_type: str, target_ref: str) -> list[GraphNodeDTO]:
        normalized_type = target_type.strip().lower()
        normalized_ref = target_ref.strip()
        normalized_ref_lower = normalized_ref.lower()
        nodes = repository.graph_nodes
        if normalized_type == "file":
            expected_id = node_id("file", normalized_ref)
            return [
                node
                for node in nodes
                if node.id == expected_id
                or node.type == "file"
                and (
                    (node.file_path or "").lower() == normalized_ref_lower
                    or (node.scope_path or "").lower() == normalized_ref_lower
                    or node.label.lower() == Path(normalized_ref).name.lower()
                )
            ]
        if normalized_type == "endpoint":
            return [
                node
                for node in nodes
                if node.type == "endpoint"
                and (
                    node.id == normalized_ref
                    or node.label.lower() == normalized_ref_lower
                    or node.label.lower().endswith(f" {normalized_ref_lower}")
                    or normalized_ref_lower in node.label.lower()
                )
            ]
        if normalized_type in {"symbol", "function", "method", "class", "component", "model", "schema"}:
            allowed_types = SYMBOL_NODE_TYPES if normalized_type == "symbol" else {normalized_type}
            return [
                node
                for node in nodes
                if node.type in allowed_types
                and (
                    node.id == normalized_ref
                    or node.label.lower() == normalized_ref_lower
                    or f"{node.file_path}:{node.label}".lower() == normalized_ref_lower
                )
            ]
        return [
            node
            for node in nodes
            if node.id == normalized_ref
            or node.label.lower() == normalized_ref_lower
            or (node.file_path or "").lower() == normalized_ref_lower
        ]

    def _traverse(self, repository: RepositoryState, roots: list[GraphNodeDTO], max_depth: int) -> list[TraversalHit]:
        nodes_by_id = {node.id: node for node in repository.graph_nodes}
        adjacency = self._adjacency(repository.graph_edges)
        root_ids = {node.id for node in roots}
        queue = deque((node.id, 0, 1.0, None, tuple()) for node in roots)
        best_depth_by_node = {node.id: 0 for node in roots}
        hits: list[TraversalHit] = []

        while queue:
            current_id, depth, confidence, via_edge, path_edge_types = queue.popleft()
            if depth >= max_depth:
                continue
            for edge, neighbor_id in adjacency.get(current_id, []):
                if neighbor_id in root_ids:
                    continue
                next_depth = depth + 1
                existing_depth = best_depth_by_node.get(neighbor_id)
                if existing_depth is not None and existing_depth <= next_depth:
                    continue
                neighbor = nodes_by_id.get(neighbor_id)
                if neighbor is None:
                    continue
                next_confidence = round(confidence * edge.confidence, 4)
                next_path = (*path_edge_types, edge.type)
                best_depth_by_node[neighbor_id] = next_depth
                hit = TraversalHit(neighbor, next_depth, next_confidence, edge, next_path)
                hits.append(hit)
                queue.append((neighbor_id, next_depth, next_confidence, edge, next_path))

        return sorted(hits, key=lambda hit: (hit.depth, -hit.confidence, hit.node.type, hit.node.label))

    def _adjacency(self, edges: list[GraphEdgeDTO]) -> dict[str, list[tuple[GraphEdgeDTO, str]]]:
        adjacency: dict[str, list[tuple[GraphEdgeDTO, str]]] = {}
        for edge in edges:
            adjacency.setdefault(edge.source, []).append((edge, edge.target))
            adjacency.setdefault(edge.target, []).append((edge, edge.source))
        return adjacency

    def _impact_item(self, hit: TraversalHit) -> ImpactItemDTO:
        return ImpactItemDTO(
            node_id=hit.node.id,
            node_type=hit.node.type,
            label=hit.node.label,
            file_path=hit.node.file_path,
            depth=hit.depth,
            confidence=hit.confidence,
            via_edge=hit.via_edge.type if hit.via_edge else None,
            reason=self._reason(hit),
        )

    def _target(self, node: GraphNodeDTO) -> ImpactTargetDTO:
        return ImpactTargetDTO(
            node_id=node.id,
            node_type=node.type,
            label=node.label,
            file_path=node.file_path,
            line_range=self._line_range(node),
        )

    def _reason(self, hit: TraversalHit) -> str:
        via = hit.via_edge.type if hit.via_edge else "graph"
        if via == "imports_internal":
            return "Connected through an internal import relation."
        if via == "calls":
            return "Connected through a function or method call."
        if via == "calls_api":
            return "Connected through a frontend or client API call."
        if via == "exposes_endpoint":
            return "Connected to an API endpoint handler."
        if via == "defines":
            return "Defined by an affected file."
        if via == "contains":
            return "Contained in an affected project area."
        if via and via.startswith("dfg_"):
            return "Connected through data-flow analysis."
        if via and via.startswith("cfg_"):
            return "Connected through control-flow analysis."
        return "Connected through the project graph."

    def _line_range(self, node: GraphNodeDTO) -> str | None:
        if node.start_line is None:
            return None
        return f"{node.start_line}-{node.end_line or node.start_line}"

    def _unique_items(self, items: list[ImpactItemDTO], key) -> list[ImpactItemDTO]:
        seen: set[str] = set()
        result: list[ImpactItemDTO] = []
        for item in sorted(items, key=lambda value: (value.depth, -value.confidence, value.label)):
            item_key = key(item)
            if not item_key or item_key in seen:
                continue
            seen.add(item_key)
            result.append(item)
        return result

    def _risk_score(
        self,
        direct: list[ImpactItemDTO],
        indirect: list[ImpactItemDTO],
        endpoints: list[ImpactItemDTO],
        tests: list[ImpactItemDTO],
    ) -> int:
        score = min(100, len(direct) * 8 + len(indirect) * 3 + len(endpoints) * 14)
        if not tests and (direct or indirect):
            score += 12
        if any(item.via_edge in HIGH_RISK_EDGE_TYPES for item in direct):
            score += 10
        return min(100, score)

    def _risk_level(self, score: int) -> str:
        if score >= 70:
            return "high"
        if score >= 35:
            return "medium"
        if score > 0:
            return "low"
        return "unknown"

    def _is_test_node(self, node: GraphNodeDTO) -> bool:
        path = node.file_path or node.scope_path or ""
        normalized = path.replace("\\", "/").lower()
        return normalized.startswith("tests/") or "/tests/" in normalized or Path(normalized).name.startswith("test_")

    def _suggested_checks(
        self,
        root: GraphNodeDTO,
        endpoints: list[ImpactItemDTO],
        tests: list[ImpactItemDTO],
        files: list[ImpactItemDTO],
    ) -> list[str]:
        checks: list[str] = []
        if root.file_path:
            checks.append(f"Review direct changes around {root.file_path}.")
        for endpoint in endpoints[:3]:
            checks.append(f"Exercise endpoint {endpoint.label}.")
        for test in tests[:3]:
            checks.append(f"Run or inspect related test file {test.file_path or test.label}.")
        if not tests and files:
            checks.append("No related tests were found in the current graph; add or run focused regression checks manually.")
        checks.append("Re-index after code changes so stale citations and graph relations are refreshed.")
        return checks

    def _missing_relations(self, repository: RepositoryState, tests: list[ImpactItemDTO]) -> list[str]:
        missing: list[str] = []
        if not tests:
            missing.append("No tested_by relation is available yet; test impact is inferred from import/file graph only.")
        if not any(edge.type.startswith("dfg_") for edge in repository.graph_edges):
            missing.append("No data-flow graph edges are available for this repository or configuration.")
        return missing
