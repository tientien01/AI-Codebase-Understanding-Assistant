from __future__ import annotations

from pathlib import Path

from app.schemas.api import GraphEdgeDTO, GraphNodeDTO, GraphResponse
from app.services.index_models import RepositoryState
from app.services.text_utils import node_id, normalize_route


class GraphService:
    def get_graph(self, repository: RepositoryState) -> GraphResponse:
        return GraphResponse(nodes=repository.graph_nodes, edges=repository.graph_edges)

    def build_graph(self, repository: RepositoryState) -> None:
        nodes: dict[str, GraphNodeDTO] = {node.id: node for node in repository.graph_nodes}
        edges: list[GraphEdgeDTO] = list(repository.graph_edges)
        root_id = node_id("folder", ".")
        nodes[root_id] = GraphNodeDTO(id=root_id, type="folder", label=repository.name, coverage="mapped", scope_path="", role="Project")

        for file_record in repository.files:
            self._add_folder_path(nodes, edges, root_id, file_record.path)
            file_id = node_id("file", file_record.path)
            parent_id = self._folder_id_for_file(file_record.path)
            nodes[file_id] = GraphNodeDTO(
                id=file_id,
                type="file",
                label=Path(file_record.path).name,
                file_path=file_record.path,
                coverage="deep_indexed",
                scope_path=file_record.path,
                role=self._file_role(file_record.path, file_record.language),
            )
            edges.append(GraphEdgeDTO(source=parent_id, target=file_id, type="contains", confidence=0.95, evidence_level="map"))

        for symbol in repository.symbols:
            file_id = node_id("file", symbol.file_path)
            nodes[symbol.id] = GraphNodeDTO(
                id=symbol.id,
                type=symbol.symbol_type,
                label=symbol.name,
                file_path=symbol.file_path,
                coverage="deep_indexed",
                scope_path=symbol.file_path,
                role=symbol.symbol_type,
            )
            edges.append(GraphEdgeDTO(source=file_id, target=symbol.id, type="defines", confidence=0.95))

        handler_symbols = {
            (symbol.file_path, symbol.name): symbol.id
            for symbol in repository.symbols
            if symbol.symbol_type in {"function", "method"}
        }
        for endpoint in repository.endpoints:
            endpoint_id = node_id("endpoint", f"{endpoint.method}:{endpoint.path}")
            handler_id = handler_symbols.get((endpoint.file_path, endpoint.handler))
            nodes[endpoint_id] = GraphNodeDTO(
                id=endpoint_id,
                type="endpoint",
                label=f"{endpoint.method} {endpoint.path}",
                file_path=endpoint.file_path,
                coverage="deep_indexed",
                scope_path=endpoint.file_path,
                role="API endpoint",
            )
            if handler_id:
                edges.append(GraphEdgeDTO(source=endpoint_id, target=handler_id, type="exposes_endpoint", confidence=0.9))

        endpoint_by_path = {normalize_route(endpoint.path): endpoint for endpoint in repository.endpoints}
        for graph_node in list(repository.graph_nodes):
            if graph_node.type != "api_call":
                continue
            route = graph_node.label.split(" ", 1)[-1]
            normalized_route = normalize_route(route)
            endpoint = endpoint_by_path.get(normalized_route)
            if endpoint is None:
                endpoint = next(
                    (
                        candidate
                        for candidate in repository.endpoints
                        if normalized_route.endswith(normalize_route(candidate.path))
                    ),
                    None,
                )
            if not endpoint:
                continue
            endpoint_id = node_id("endpoint", f"{endpoint.method}:{endpoint.path}")
            edges.append(GraphEdgeDTO(source=graph_node.id, target=endpoint_id, type="calls_api", confidence=0.72))

        repository.graph_nodes = list(nodes.values())
        repository.graph_edges = edges

    def _add_folder_path(self, nodes: dict[str, GraphNodeDTO], edges: list[GraphEdgeDTO], root_id: str, file_path: str) -> None:
        parts = Path(file_path).parts[:-1]
        parent_id = root_id
        current_parts: list[str] = []
        for part in parts:
            current_parts.append(part)
            folder_path = "/".join(current_parts)
            folder_id = node_id("folder", folder_path)
            nodes.setdefault(
                folder_id,
                GraphNodeDTO(
                    id=folder_id,
                    type="folder",
                    label=part,
                    coverage="mapped",
                    scope_path=folder_path,
                    role=self._folder_role(folder_path),
                ),
            )
            edges.append(GraphEdgeDTO(source=parent_id, target=folder_id, type="contains", confidence=0.85, evidence_level="map"))
            parent_id = folder_id

    def _folder_id_for_file(self, file_path: str) -> str:
        parent = Path(file_path).parent.as_posix()
        return node_id("folder", "." if parent == "." else parent)

    def _folder_role(self, folder_path: str) -> str:
        lower = folder_path.lower()
        if "frontend" in lower or lower.startswith("apps/web"):
            return "Frontend area"
        if "backend" in lower or "service" in lower:
            return "Backend service"
        if "test" in lower:
            return "Tests"
        if "doc" in lower:
            return "Documentation"
        return "Project area"

    def _file_role(self, file_path: str, language: str) -> str:
        name = Path(file_path).name.lower()
        if name.startswith("readme"):
            return "Documentation"
        if name in {"main.py", "app.py", "server.py"}:
            return "Entrypoint"
        if "route" in file_path.lower() or "controller" in file_path.lower():
            return "API routing"
        return f"{language.title()} file"
