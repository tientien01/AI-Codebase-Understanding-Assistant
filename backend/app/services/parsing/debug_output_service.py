from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas.api import GraphNodeDTO
from app.services.code_analysis.stable_ids import stable_edge_id, stable_node_id
from app.services.index_models import RepositoryState
from app.services.text_utils import node_id, utc_now


class ParseDebugOutputService:
    """Writes a parser-facing debug artifact without coupling parser code to storage."""

    artifact_name = "parse_output.json"
    schema_version = "parse-debug-v1"

    def write(self, repository: RepositoryState) -> Path:
        artifact_path = settings.repository_storage_dir / repository.id / self.artifact_name
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._payload(repository, artifact_path)
        self._write_json(artifact_path, payload)
        self._write_source_mirror(repository, payload)
        return artifact_path

    def _write_source_mirror(self, repository: RepositoryState, payload: dict[str, Any]) -> None:
        if not repository.source_path.exists():
            return
        mirror_path = repository.source_path / ".ai-codebase" / self.artifact_name
        mirror_payload = {
            **payload,
            "metadata": {
                **payload["metadata"],
                "artifact_path": str(mirror_path),
                "primary_artifact_path": payload["metadata"]["artifact_path"],
            },
        }
        try:
            self._write_json(mirror_path, mirror_payload)
        except OSError:
            return

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(path)

    def _payload(self, repository: RepositoryState, artifact_path: Path) -> dict[str, Any]:
        graph_node_by_id = {node.id: node for node in repository.graph_nodes}
        nodes = self._nodes(repository, graph_node_by_id)
        node_ids = {node["id"] for node in nodes}
        edges = self._edges(repository, node_ids)
        files = [
            {
                "path": file.path,
                "language": file.language,
                "file_type": file.file_type,
                "size_bytes": file.size_bytes,
                "content_hash": file.content_hash,
                "parse_status": file.parse_status,
            }
            for file in sorted(repository.files, key=lambda item: item.path)
        ]
        return {
            "metadata": {
                "schema_version": self.schema_version,
                "repository_id": repository.id,
                "repository_name": repository.name,
                "index_version": repository.current_index_version,
                "generated_at": utc_now(),
                "artifact_path": str(artifact_path),
                "files_count": len(repository.files),
                "nodes_count": len(nodes),
                "edges_count": len(edges),
                "warnings_count": len(repository.warnings),
                "errors_count": len(repository.failed_file_records),
            },
            "files": files,
            "nodes": nodes,
            "edges": edges,
            "warnings": list(repository.warnings),
            "errors": list(repository.failed_file_records),
            "diagnostics": list(repository.parse_diagnostics),
            "skipped_files": list(repository.skipped_file_records),
        }

    def _nodes(self, repository: RepositoryState, graph_node_by_id: dict[str, GraphNodeDTO]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for file in repository.files:
            nodes.append(
                {
                    "id": node_id("file", file.path),
                    "kind": "File",
                    "label": file.path,
                    "file_path": file.path,
                    "language": file.language,
                    "parse_status": file.parse_status,
                    "content_hash": file.content_hash,
                }
            )
        for symbol in repository.symbols:
            nodes.append(
                {
                    "id": symbol.id,
                    "kind": self._symbol_kind(symbol.symbol_type),
                    "label": symbol.name,
                    "file_path": symbol.file_path,
                    "start_line": symbol.start_line,
                    "end_line": symbol.end_line,
                    "signature": symbol.signature,
                }
            )
        for edge in repository.graph_edges:
            if edge.type != "imports":
                continue
            module_node = graph_node_by_id.get(edge.target)
            nodes.append(
                {
                    "id": stable_node_id(repository.id, "import", f"{edge.source}:{edge.target}"),
                    "kind": "Import",
                    "label": module_node.label if module_node else edge.target,
                    "source_id": edge.source,
                    "target_id": edge.target,
                    "confidence": edge.confidence,
                    "resolved": edge.target in graph_node_by_id,
                }
            )
        for graph_node in repository.graph_nodes:
            if graph_node.type == "call_site":
                nodes.append(
                    {
                        "id": graph_node.id,
                        "kind": "Call",
                        "label": graph_node.label,
                        "file_path": graph_node.file_path,
                        "scope_path": graph_node.scope_path,
                        "resolved": True,
                    }
                )
            elif graph_node.type == "unresolved_call":
                nodes.append(
                    {
                        "id": graph_node.id,
                        "kind": "Call",
                        "label": graph_node.label,
                        "file_path": graph_node.file_path,
                        "scope_path": graph_node.scope_path,
                        "resolved": False,
                    }
                )
            elif graph_node.type == "cfg_node" and graph_node.role in {"ASSIGNMENT", "RETURN"}:
                nodes.append(
                    {
                        "id": graph_node.id,
                        "kind": "Assign" if graph_node.role == "ASSIGNMENT" else "Return",
                        "label": graph_node.label,
                        "file_path": graph_node.file_path,
                        "scope_path": graph_node.scope_path,
                    }
                )
        known_ids = {node["id"] for node in nodes}
        for graph_node in repository.graph_nodes:
            if graph_node.id in known_ids:
                continue
            nodes.append(
                {
                    "id": graph_node.id,
                    "kind": self._graph_node_kind(graph_node),
                    "label": graph_node.label,
                    "file_path": graph_node.file_path,
                    "scope_path": graph_node.scope_path,
                    "role": graph_node.role,
                }
            )
        return self._dedupe_nodes(nodes)

    def _edges(self, repository: RepositoryState, node_ids: set[str]) -> list[dict[str, Any]]:
        edges: list[dict[str, Any]] = []
        for edge in repository.graph_edges:
            edges.append(
                {
                    "id": stable_edge_id(repository.id, edge.source, edge.target, edge.type, self._owning_file(edge.source, node_ids)),
                    "type": edge.type,
                    "source": edge.source,
                    "target": edge.target,
                    "confidence": edge.confidence,
                    "evidence_level": edge.evidence_level,
                    "resolved": edge.source in node_ids and edge.target in node_ids,
                }
            )
        return edges

    def _dedupe_nodes(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for node in nodes:
            deduped[node["id"]] = {**deduped.get(node["id"], {}), **node}
        return list(deduped.values())

    def _owning_file(self, source_id: str, node_ids: set[str]) -> str:
        return source_id if source_id in node_ids else "unknown"

    def _symbol_kind(self, symbol_type: str) -> str:
        return {
            "class": "Class",
            "schema": "Class",
            "model": "Class",
            "function": "Function",
            "method": "Method",
            "component": "Function",
        }.get(symbol_type, symbol_type.title())

    def _graph_node_kind(self, node: GraphNodeDTO) -> str:
        return {
            "module": "ImportTarget",
            "endpoint": "Endpoint",
            "api_call": "Call",
            "cfg_node": "CFG",
            "dfg_node": "DataFlow",
            "folder": "Folder",
            "file": "File",
        }.get(node.type, node.type.title())
