from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from app.schemas.api import GraphNodeDTO
from app.services.chunking_service import ChunkingService
from app.services.index_models import EndpointRecord, RepositoryState, SymbolRecord


class SemanticEnrichmentService:
    """Adds deterministic semantic metadata without requiring an LLM provider."""

    def __init__(self, chunking: ChunkingService) -> None:
        self.chunking = chunking

    def enrich(self, repository: RepositoryState) -> None:
        symbols_by_file = self._symbols_by_file(repository)
        endpoints_by_file = self._endpoints_by_file(repository)
        degree_by_node = self._degree_by_node(repository)
        for node in repository.graph_nodes:
            self._enrich_node(node, symbols_by_file, endpoints_by_file, degree_by_node)
        self._add_semantic_summary_chunks(repository, symbols_by_file, endpoints_by_file)

    def _enrich_node(
        self,
        node: GraphNodeDTO,
        symbols_by_file: dict[str, list[SymbolRecord]],
        endpoints_by_file: dict[str, list[EndpointRecord]],
        degree_by_node: Counter[str],
    ) -> None:
        file_path = node.file_path or node.scope_path
        symbols = symbols_by_file.get(file_path or "", [])
        endpoints = endpoints_by_file.get(file_path or "", [])
        node.tags = self._tags(node, symbols, endpoints)
        node.layer = self._layer(node, symbols, endpoints)
        node.complexity = self._complexity(node, degree_by_node[node.id])
        node.summary = self._summary(node, symbols, endpoints)
        node.metadata = {
            **node.metadata,
            "enrichment": "heuristic-v1",
            "semantic_tags": ",".join(node.tags),
        }

    def _add_semantic_summary_chunks(
        self,
        repository: RepositoryState,
        symbols_by_file: dict[str, list[SymbolRecord]],
        endpoints_by_file: dict[str, list[EndpointRecord]],
    ) -> None:
        existing = {(chunk.file_path, chunk.chunk_type) for chunk in repository.chunks}
        for file in repository.files:
            if (file.path, "semantic_summary") in existing:
                continue
            symbols = symbols_by_file.get(file.path, [])
            endpoints = endpoints_by_file.get(file.path, [])
            content = self._file_summary(file.path, file.language, symbols, endpoints)
            self.chunking.add_chunk(repository, file.path, "semantic_summary", content, 1, 1, Path(file.path).name)

    def _summary(
        self,
        node: GraphNodeDTO,
        symbols: list[SymbolRecord],
        endpoints: list[EndpointRecord],
    ) -> str:
        if node.type == "file" and node.file_path:
            return self._file_summary(node.file_path, "source", symbols, endpoints)
        if node.type == "endpoint":
            return f"API endpoint {node.label} handled in {node.file_path or 'an indexed source file'}."
        if node.type in {"function", "method", "class", "schema", "model", "component"}:
            location = f" in {node.file_path}" if node.file_path else ""
            line_range = f" lines {node.start_line}-{node.end_line}" if node.start_line else ""
            return f"{node.type.replace('_', ' ').title()} {node.label}{location}{line_range}."
        if node.type == "folder":
            return f"Project area {node.label} groups related indexed files."
        return node.summary or f"{node.type.replace('_', ' ').title()} {node.label}."

    def _file_summary(
        self,
        file_path: str,
        language: str,
        symbols: list[SymbolRecord],
        endpoints: list[EndpointRecord],
    ) -> str:
        symbol_names = ", ".join(symbol.name for symbol in symbols[:8]) or "no named symbols"
        endpoint_names = ", ".join(f"{endpoint.method} {endpoint.path}" for endpoint in endpoints[:5])
        parts = [
            f"{file_path} is a {language} file",
            f"defines {symbol_names}",
        ]
        if endpoint_names:
            parts.append(f"exposes {endpoint_names}")
        parts.append(f"layer {self._layer_from_path(file_path)}")
        return "; ".join(parts) + "."

    def _tags(
        self,
        node: GraphNodeDTO,
        symbols: list[SymbolRecord],
        endpoints: list[EndpointRecord],
    ) -> list[str]:
        raw_tags = [node.type, node.layer or "", self._layer_from_path(node.file_path or node.scope_path or "")]
        haystack = " ".join(
            [
                node.label,
                node.file_path or "",
                " ".join(symbol.name for symbol in symbols),
                " ".join(endpoint.path for endpoint in endpoints),
            ]
        ).lower()
        for token in ("auth", "login", "user", "token", "api", "config", "database", "test", "frontend", "backend"):
            if token in haystack:
                raw_tags.append(token)
        if endpoints or node.type == "endpoint":
            raw_tags.append("api")
        return self._dedupe_tags(raw_tags)

    def _layer(self, node: GraphNodeDTO, symbols: list[SymbolRecord], endpoints: list[EndpointRecord]) -> str:
        if endpoints or node.type == "endpoint":
            return "api"
        if any(symbol.symbol_type in {"model", "schema"} for symbol in symbols) or node.type in {"model", "schema"}:
            return "data"
        return self._layer_from_path(node.file_path or node.scope_path or "")

    def _layer_from_path(self, file_path: str) -> str:
        lower = file_path.lower().replace("\\", "/")
        parts = set(Path(lower).parts)
        if "frontend" in parts or lower.endswith((".tsx", ".jsx", ".css", ".html")):
            return "frontend"
        if "tests" in parts or Path(lower).name.startswith("test_"):
            return "tests"
        if "docs" in parts or lower.endswith(".md"):
            return "documentation"
        if "api" in parts or "routes" in parts or "router" in lower:
            return "api"
        if "models" in parts or "schemas" in parts:
            return "data"
        if "backend" in parts or lower.endswith(".py"):
            return "backend"
        return "application"

    def _complexity(self, node: GraphNodeDTO, degree: int) -> str:
        span = (node.end_line or node.start_line or 0) - (node.start_line or 0) + 1
        if node.type in {"folder", "module"}:
            return "low"
        if degree >= 12 or span >= 120:
            return "high"
        if degree >= 5 or span >= 35 or node.type in {"cfg_node", "dfg_node", "unresolved_call"}:
            return "medium"
        return "low"

    def _symbols_by_file(self, repository: RepositoryState) -> dict[str, list[SymbolRecord]]:
        grouped: dict[str, list[SymbolRecord]] = defaultdict(list)
        for symbol in repository.symbols:
            grouped[symbol.file_path].append(symbol)
        return grouped

    def _endpoints_by_file(self, repository: RepositoryState) -> dict[str, list[EndpointRecord]]:
        grouped: dict[str, list[EndpointRecord]] = defaultdict(list)
        for endpoint in repository.endpoints:
            grouped[endpoint.file_path].append(endpoint)
        return grouped

    def _degree_by_node(self, repository: RepositoryState) -> Counter[str]:
        degree: Counter[str] = Counter()
        for edge in repository.graph_edges:
            degree[edge.source] += 1
            degree[edge.target] += 1
        return degree

    def _dedupe_tags(self, tags: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for tag in tags:
            value = tag.strip().lower().replace(" ", "_")
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result
