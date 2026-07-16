from __future__ import annotations

import shutil
import re
from collections import defaultdict
from pathlib import Path

from app.core.config import settings
from app.core.errors import DomainError
from app.schemas.api import (
    EndpointDTO,
    EndpointListResponse,
    ImportantFileDTO,
    ModuleDTO,
    OverviewResponse,
    ReadingPathItemDTO,
    ReadingPathResponse,
    ReadingPathSignalDTO,
    RepositoryBulkDeleteResponse,
    RepositoryCreateResponse,
    RepositoryDeleteResponse,
    RepositoryDTO,
    SymbolDTO,
    SymbolListResponse,
)
from app.schemas.exploration import (
    ArchitectureComponentDTO,
    ArchitectureEvidenceDTO,
    ArchitectureFlowDTO,
    ArchitectureFlowStepDTO,
    ArchitectureOverviewDTO,
    ArchitectureRelationDTO,
)
from app.services.index_models import RepositoryState
from app.services.architecture import RuleBasedArchitectureEngine
from app.services.language_registry import LANGUAGE_DEFINITIONS
from app.services.repositories.repository_port import RepositoryStorePort
from app.services.text_utils import node_id, read_text


class RepositoryService:
    def __init__(self, store: RepositoryStorePort) -> None:
        self.store = store
        self.architecture_engine = RuleBasedArchitectureEngine()
        self.repositories: dict[str, RepositoryState] = {
            repository.id: repository for repository in self.store.list_repositories()
        }

    def list_repositories(self) -> list[RepositoryDTO]:
        return [self.repository_dto(repository) for repository in self.repositories.values()]

    def create_repository(self, repository: RepositoryState) -> RepositoryCreateResponse:
        self.repositories[repository.id] = repository
        self.persist_repository(repository)
        return RepositoryCreateResponse(
            repository_id=repository.id,
            name=repository.name,
            status=repository.status,
            source_type=repository.source_type,
        )

    def delete_repository(self, repository_id: str, clear_evidence) -> RepositoryDeleteResponse:
        repository = self.get_repository(repository_id)
        self.store.delete_repository(repository_id)
        self.repositories.pop(repository_id, None)
        self._delete_managed_storage(repository)
        clear_evidence(repository_id)
        return RepositoryDeleteResponse(deleted=True, repository_id=repository_id)

    def delete_repositories(self, repository_ids: list[str], clear_evidence) -> RepositoryBulkDeleteResponse:
        deleted_ids: list[str] = []
        for repository_id in repository_ids:
            repository = self.repositories.get(repository_id)
            if repository is None:
                continue
            self.store.delete_repository(repository_id)
            self.repositories.pop(repository_id, None)
            self._delete_managed_storage(repository)
            clear_evidence(repository_id)
            deleted_ids.append(repository_id)
        return RepositoryBulkDeleteResponse(deleted_count=len(deleted_ids), repository_ids=deleted_ids)

    def persist_repository(self, repository: RepositoryState) -> None:
        self.store.save_repository(repository)

    def persist_repository_metadata(self, repository: RepositoryState) -> None:
        self.store.save_repository_metadata(repository)

    def replace_repository_index(self, repository: RepositoryState, indexed_repository: RepositoryState) -> None:
        repository.status = indexed_repository.status
        repository.current_index_version = indexed_repository.current_index_version
        repository.files = indexed_repository.files
        repository.symbols = indexed_repository.symbols
        repository.endpoints = indexed_repository.endpoints
        repository.chunks = indexed_repository.chunks
        repository.graph_nodes = indexed_repository.graph_nodes
        repository.graph_edges = indexed_repository.graph_edges
        repository.logs = indexed_repository.logs
        repository.warnings = indexed_repository.warnings
        repository.skipped_file_records = indexed_repository.skipped_file_records
        repository.failed_file_records = indexed_repository.failed_file_records
        repository.failed_files = indexed_repository.failed_files
        repository.current_step = indexed_repository.current_step
        repository.started_at = indexed_repository.started_at
        repository.finished_at = indexed_repository.finished_at

    def get_repository(self, repository_id: str) -> RepositoryState:
        repository = self.repositories.get(repository_id)
        if repository is None:
            raise DomainError("REPOSITORY_NOT_FOUND", "Repository not found.", 404, {"repository_id": repository_id})
        return repository

    def get_indexed_repository(self, repository_id: str) -> RepositoryState:
        repository = self.get_repository(repository_id)
        if repository.status not in {"indexed", "indexed_with_warnings"}:
            raise DomainError("REPOSITORY_NOT_INDEXED", "Repository has not been indexed yet.", 409, {"repository_id": repository_id})
        return repository

    def repository_dto(self, repository: RepositoryState) -> RepositoryDTO:
        return RepositoryDTO(
            id=repository.id,
            name=repository.name,
            source_type=repository.source_type,
            source_label=repository.source_label,
            source_uri=None,
            status=repository.status,
            current_index_version=repository.current_index_version,
            detected_stack=self.detect_stack(repository),
            total_files=len(repository.files),
            indexed_files=len(repository.files) if repository.status in {"indexed", "indexed_with_warnings"} else 0,
            symbols=len(repository.symbols),
            endpoints=len(repository.endpoints),
            chunks=len(repository.chunks),
            graph_nodes=len(repository.graph_nodes),
            last_indexed_at=repository.finished_at,
        )

    def important_files(self, repository: RepositoryState) -> list[ImportantFileDTO]:
        ranked: list[tuple[int, ImportantFileDTO]] = []
        for file_record in repository.files:
            name = Path(file_record.path).name.lower()
            path = file_record.path.lower()
            if name.startswith("readme"):
                ranked.append((0, ImportantFileDTO(file_path=file_record.path, reason="Project overview and setup")))
            elif name in {"main.py", "app.py", "main.ts", "main.tsx", "index.ts", "index.tsx"}:
                ranked.append((1, ImportantFileDTO(file_path=file_record.path, reason="Application entrypoint candidate")))
            elif "router" in path or "routes" in path:
                ranked.append((2, ImportantFileDTO(file_path=file_record.path, reason="API boundary")))
            elif "/services/" in f"/{path}" or name.endswith(("_service.py", "service.ts", "service.tsx")):
                ranked.append((3, ImportantFileDTO(file_path=file_record.path, reason="Application service")))
            elif any(token in f"/{path}" for token in ("/repositories/", "/models/", "/schemas/")):
                ranked.append((4, ImportantFileDTO(file_path=file_record.path, reason="Data or schema boundary")))
        return [item for _, item in sorted(ranked, key=lambda entry: (entry[0], entry[1].file_path))[:8]]

    def build_modules(self, repository: RepositoryState) -> list[ModuleDTO]:
        counts: dict[str, int] = {}
        for file_record in repository.files:
            parts = file_record.path.split("/")
            module_name = parts[-2] if len(parts) > 1 else "root"
            counts[module_name] = counts.get(module_name, 0) + 1
        return [
            ModuleDTO(name=name, summary=f"{count} indexed files in this module.", file_count=count)
            for name, count in sorted(counts.items())[:8]
        ]

    def detect_stack(self, repository: RepositoryState) -> list[str]:
        stack: set[str] = set()
        display_by_language = {
            definition.language: definition.display_name
            for definition in LANGUAGE_DEFINITIONS
            if definition.language != "config"
        }
        for file in repository.files:
            display_name = display_by_language.get(file.language)
            if display_name:
                stack.add(display_name)
        if any(file.language == "python" and self._file_contains(file.absolute_path, "fastapi") for file in repository.files):
            stack.add("FastAPI")
        if any(Path(file.path).suffix.lower() in {".tsx", ".jsx"} for file in repository.files):
            stack.add("React")
        stack.update(self.architecture_engine.detect_frameworks(repository))
        return sorted(stack)

    def documentation_gaps(self, repository: RepositoryState) -> list[str]:
        has_readme = any(Path(file.path).name.lower().startswith("readme") for file in repository.files)
        gaps = []
        if not has_readme:
            gaps.append("Repository has no README indexed.")
        if not any("test" in file.path.lower() for file in repository.files):
            gaps.append("No test files were detected.")
        if not repository.endpoints:
            gaps.append("No FastAPI endpoint was detected.")
        return gaps or ["No major documentation gap detected by MVP rules."]

    def build_architecture(self, repository: RepositoryState) -> ArchitectureOverviewDTO:
        """Build a bounded C4-lite read model from indexed facts only."""
        return self.architecture_engine.build(repository, self.detect_stack(repository))

        # Legacy v1 implementation remains below temporarily as an explicit rollback
        # reference while ARCH-001 is verified. It is unreachable in the v2 path.
        stack = self.detect_stack(repository)
        file_paths = sorted(file.path for file in repository.files)
        lower_paths = {path: path.lower() for path in file_paths}
        components: list[ArchitectureComponentDTO] = []

        def add_component(
            component_id: str,
            label: str,
            kind: str,
            layer: str,
            summary: str,
            paths: list[str] | None = None,
            technology: str | None = None,
            parent_id: str | None = None,
            endpoint_count: int = 0,
            evidence: list[ArchitectureEvidenceDTO] | None = None,
        ) -> None:
            components.append(ArchitectureComponentDTO(
                id=component_id,
                label=label,
                kind=kind,
                layer=layer,
                summary=summary,
                technology=technology,
                parent_id=parent_id,
                file_paths=sorted(set(paths or []))[:20],
                endpoint_count=endpoint_count,
                evidence=(evidence or [])[:8],
            ))

        presentation_paths = [
            path for path in file_paths
            if any(part in lower_paths[path].split("/") for part in ("frontend", "client", "web"))
            or Path(path).suffix.lower() in {".tsx", ".jsx"}
        ]
        if presentation_paths:
            add_component(
                "actor:user", "User", "actor", "actor", "Uses the indexed presentation surface.",
                evidence=[ArchitectureEvidenceDTO(type="source", detail="Presentation source files detected.", file_path=presentation_paths[0])],
            )
            presentation_label = "React Web App" if "React" in stack else "Web Interface"
            add_component(
                "presentation:web", presentation_label, "presentation", "presentation",
                "Client-facing presentation surface.", presentation_paths, "React" if "React" in stack else None,
                evidence=[ArchitectureEvidenceDTO(type="source", detail=f"{len(presentation_paths)} presentation files detected.", file_path=presentation_paths[0])],
            )

        endpoint_groups: dict[str, list] = defaultdict(list)
        for endpoint in repository.endpoints:
            endpoint_groups[self._endpoint_domain(endpoint.path, endpoint.file_path)].append(endpoint)

        backend_paths = [path for path in file_paths if path not in presentation_paths and Path(path).suffix.lower() in {".py", ".go", ".java", ".ts", ".js", ".cs", ".rs"}]
        has_backend = bool(repository.endpoints or "FastAPI" in stack or backend_paths)
        if has_backend:
            backend_technology = "FastAPI" if "FastAPI" in stack else next((item for item in stack if item not in {"React", "HTML", "CSS"}), None)
            add_component(
                "container:backend", f"{backend_technology} Backend" if backend_technology else "Application Backend",
                "container", "container", "Server-side application boundary.", backend_paths,
                backend_technology,
                evidence=[ArchitectureEvidenceDTO(type="index", detail=f"{len(repository.endpoints)} indexed endpoints and {len(backend_paths)} backend source files.")],
            )

        for domain in sorted(endpoint_groups)[:5]:
            endpoints = endpoint_groups[domain]
            paths = sorted({endpoint.file_path for endpoint in endpoints})
            label = f"{self._display_domain(domain)} API"
            add_component(
                f"api:{domain}", label, "api", "api", f"Owns {len(endpoints)} indexed endpoint{'s' if len(endpoints) != 1 else ''}.",
                paths, "FastAPI" if "FastAPI" in stack else None, "container:backend", len(endpoints),
                [ArchitectureEvidenceDTO(type="endpoint", detail=f"{endpoint.method} {endpoint.path}", file_path=endpoint.file_path) for endpoint in endpoints[:4]],
            )

        service_groups: dict[str, list[str]] = defaultdict(list)
        data_groups: dict[str, list[str]] = defaultdict(list)
        for path in backend_paths:
            normalized = f"/{lower_paths[path]}"
            stem = Path(path).stem.lower()
            if "/services/" in normalized or stem.endswith("_service") or stem.endswith("service"):
                service_groups[self._path_domain(path, ("service", "services"))].append(path)
            elif any(token in normalized for token in ("/repositories/", "/repository/")) or stem.endswith(("_repository", "repository")):
                data_groups[self._path_domain(path, ("repository", "repositories"))].append(path)
            elif any(token in normalized for token in ("/models/", "/schemas/")):
                data_groups["models"].append(path)

        for domain in sorted(service_groups)[:5]:
            paths = service_groups[domain]
            add_component(
                f"application:{domain}", f"{self._display_domain(domain)} Service", "application", "application",
                f"Application behavior implemented by {len(paths)} source file{'s' if len(paths) != 1 else ''}.", paths,
                parent_id="container:backend",
                evidence=[ArchitectureEvidenceDTO(type="source", detail="Service path and symbols detected.", file_path=paths[0])],
            )

        for domain in sorted(data_groups)[:4]:
            paths = data_groups[domain]
            label = "Data Models" if domain == "models" else f"{self._display_domain(domain)} Repository"
            add_component(
                f"data:{domain}", label, "data_access", "data_access",
                f"Data boundary represented by {len(paths)} source file{'s' if len(paths) != 1 else ''}.", paths,
                parent_id="container:backend",
                evidence=[ArchitectureEvidenceDTO(type="source", detail="Repository, model, or schema path detected.", file_path=paths[0])],
            )

        marker_sources = self._architecture_marker_sources(repository)
        infrastructure_specs = (
            ("postgresql", "PostgreSQL", "database", "SQL"),
            ("redis", "Redis", "cache", "cache"),
            ("qdrant", "Qdrant", "vector_store", "vector search"),
            ("object_storage", "Object Storage", "object_store", "artifacts"),
            ("openai", "OpenAI API", "external_api", "HTTPS"),
        )
        infrastructure_labels: list[str] = []
        for marker, label, technology, _ in infrastructure_specs:
            paths = marker_sources.get(marker, [])
            if not paths:
                continue
            infrastructure_labels.append(label)
            add_component(
                f"infrastructure:{marker}", label, "infrastructure", "infrastructure",
                f"Detected from {len(paths)} indexed source or dependency file{'s' if len(paths) != 1 else ''}.",
                paths, technology,
                evidence=[ArchitectureEvidenceDTO(type="technology_marker", detail=f"{label} marker detected.", file_path=path) for path in paths[:4]],
            )

        relations = self._architecture_relations(repository, components, infrastructure_specs)
        flows = self._architecture_flows(repository, components, relations, endpoint_groups)
        technologies = sorted(set(stack + infrastructure_labels))
        system_type, summary = self._architecture_identity(stack, bool(repository.endpoints), bool(presentation_paths), infrastructure_labels)
        confirmed_count = len([relation for relation in relations if relation.support == "confirmed"])
        unknowns: list[str] = []
        if not repository.graph_edges:
            unknowns.append("Cross-component graph evidence is unavailable; structural connections remain inferred.")
        if not infrastructure_labels:
            unknowns.append("No infrastructure technology was confirmed from indexed source markers.")
        if not repository.endpoints and not service_groups:
            unknowns.append("No API or application-service boundary was detected.")
        coverage_state = "ready" if len(components) >= 3 and (confirmed_count > 0 or len(repository.endpoints) > 0) else "limited"
        return ArchitectureOverviewDTO(
            system_type=system_type,
            summary=summary,
            technologies=technologies[:10],
            components=components[:24],
            relations=relations[:32],
            primary_flows=flows[:3],
            coverage_state=coverage_state,
            unknowns=unknowns[:5],
        )

    def _architecture_relations(
        self,
        repository: RepositoryState,
        components: list[ArchitectureComponentDTO],
        infrastructure_specs: tuple,
    ) -> list[ArchitectureRelationDTO]:
        by_id = {component.id: component for component in components}
        relation_map: dict[tuple[str, str, str], ArchitectureRelationDTO] = {}

        def add(source: str, target: str, label: str, support: str, evidence: list[ArchitectureEvidenceDTO]) -> None:
            if source == target or source not in by_id or target not in by_id:
                return
            key = (source, target, label)
            existing = relation_map.get(key)
            if existing is None or (existing.support != "confirmed" and support == "confirmed"):
                relation_map[key] = ArchitectureRelationDTO(source=source, target=target, label=label, support=support, evidence=evidence[:6])

        if "actor:user" in by_id and "presentation:web" in by_id:
            add("actor:user", "presentation:web", "uses", "inferred", by_id["presentation:web"].evidence)

        leaf_components = [component for component in components if component.kind not in {"actor", "container", "infrastructure"}]
        file_owner: dict[str, str] = {}
        for component in leaf_components:
            for path in component.file_paths:
                file_owner.setdefault(path, component.id)
        node_owner = {
            node.id: file_owner[node.file_path]
            for node in repository.graph_nodes
            if node.file_path in file_owner
        }
        edge_labels = {
            "calls_api": "HTTPS / API",
            "exposes_endpoint": "routes to",
            "calls": "calls",
            "imports": "imports",
            "depends_on": "depends on",
            "reads": "reads",
            "writes": "writes",
        }
        for edge in sorted(repository.graph_edges, key=lambda item: (item.source, item.target, item.type)):
            source = node_owner.get(edge.source)
            target = node_owner.get(edge.target)
            if source is None or target is None or source == target or edge.type.lower() in {"defined_in", "contains"}:
                continue
            support = "confirmed" if edge.evidence_level != "inferred" and edge.confidence >= 0.75 else "inferred"
            label = edge_labels.get(edge.type.lower(), edge.type.replace("_", " ").lower())
            source_path = next((node.file_path for node in repository.graph_nodes if node.id == edge.source), None)
            add(source, target, label, support, [ArchitectureEvidenceDTO(type="graph_edge", detail=f"{edge.type} ({edge.confidence:.2f})", file_path=source_path)])

        presentation = by_id.get("presentation:web")
        backend = by_id.get("container:backend")
        if presentation and backend:
            add(presentation.id, backend.id, "HTTPS / JSON", "inferred", presentation.evidence)

        api_components = [component for component in components if component.kind == "api"]
        service_components = [component for component in components if component.kind == "application"]
        data_components = [component for component in components if component.kind == "data_access"]
        for api in api_components:
            domain = api.id.split(":", 1)[1]
            matching = next((service for service in service_components if service.id.endswith(f":{domain}") or domain in service.label.lower()), None)
            if matching:
                add(api.id, matching.id, "calls", "inferred", api.evidence + matching.evidence)
        for service in service_components:
            domain = service.id.split(":", 1)[1]
            matching = next((data for data in data_components if data.id.endswith(f":{domain}") or domain in data.label.lower()), None)
            if matching is None and len(data_components) == 1:
                matching = data_components[0]
            if matching:
                add(service.id, matching.id, "reads / writes", "inferred", service.evidence + matching.evidence)

        for marker, _, _, label in infrastructure_specs:
            target = f"infrastructure:{marker}"
            if target not in by_id:
                continue
            evidence = by_id[target].evidence
            evidence_paths = set(by_id[target].file_paths)
            source = next((component.id for component in service_components + data_components if evidence_paths.intersection(component.file_paths)), "container:backend")
            add(source, target, label, "confirmed", evidence)

        order = {"confirmed": 0, "inferred": 1, "unknown": 2}
        return sorted(relation_map.values(), key=lambda item: (order[item.support], item.source, item.target, item.label))

    def _architecture_flows(
        self,
        repository: RepositoryState,
        components: list[ArchitectureComponentDTO],
        relations: list[ArchitectureRelationDTO],
        endpoint_groups: dict[str, list],
    ) -> list[ArchitectureFlowDTO]:
        by_id = {component.id: component for component in components}
        outgoing: dict[str, list[ArchitectureRelationDTO]] = defaultdict(list)
        kind_order = {"application": 0, "data_access": 1, "infrastructure": 2, "container": 3, "api": 4, "presentation": 5, "actor": 6, "module": 7}
        for relation in relations:
            outgoing[relation.source].append(relation)
        for relation_list in outgoing.values():
            relation_list.sort(key=lambda relation: (0 if relation.support == "confirmed" else 1, kind_order.get(by_id[relation.target].kind, 9), relation.target))

        flows: list[ArchitectureFlowDTO] = []
        for domain in sorted(endpoint_groups)[:3]:
            endpoint = sorted(endpoint_groups[domain], key=lambda item: (item.path, item.method))[0]
            api_id = f"api:{domain}"
            if api_id not in by_id:
                continue
            steps: list[ArchitectureFlowStepDTO] = []
            if "presentation:web" in by_id:
                steps.append(ArchitectureFlowStepDTO(component_id="presentation:web", label=by_id["presentation:web"].label, support="inferred"))
            steps.append(ArchitectureFlowStepDTO(component_id=api_id, label=by_id[api_id].label, support="confirmed"))
            current = api_id
            visited = {api_id, "presentation:web"}
            while len(steps) < 6:
                relation = next((candidate for candidate in outgoing.get(current, []) if candidate.target not in visited and by_id[candidate.target].kind != "container"), None)
                if relation is None:
                    break
                visited.add(relation.target)
                steps.append(ArchitectureFlowStepDTO(component_id=relation.target, label=by_id[relation.target].label, support=relation.support))
                current = relation.target
            flow_parts = [part for part in endpoint.path.strip("/").split("/") if part and part.lower() not in {"api", "v1", "v2", "v3"} and not part.startswith("{")]
            flow_name = self._display_domain(flow_parts[-1] if flow_parts else domain)
            flows.append(ArchitectureFlowDTO(
                id=f"flow:{self._slug(endpoint.method)}:{self._slug(endpoint.path)}",
                label=f"{flow_name} flow",
                summary=f"{endpoint.method} {endpoint.path}",
                steps=steps,
                evidence=[ArchitectureEvidenceDTO(type="endpoint", detail=f"{endpoint.method} {endpoint.path}", file_path=endpoint.file_path)],
            ))
        return flows

    def _architecture_marker_sources(self, repository: RepositoryState) -> dict[str, list[str]]:
        markers = {
            "postgresql": ("postgresql", "postgres://", "psycopg", "asyncpg"),
            "redis": ("redis",),
            "qdrant": ("qdrant",),
            "object_storage": ("boto3", "minio", "object_storage"),
            "openai": ("openai",),
        }
        matches: dict[str, list[str]] = defaultdict(list)
        for file in repository.files:
            if not self._safe_architecture_source(file.path):
                continue
            try:
                content = read_text(file.absolute_path).lower()
            except OSError:
                continue
            for marker, values in markers.items():
                if any(value in content for value in values):
                    matches[marker].append(file.path)
        return {marker: sorted(set(paths))[:8] for marker, paths in matches.items()}

    @staticmethod
    def _safe_architecture_source(path: str) -> bool:
        normalized = path.replace("\\", "/").lower()
        name = normalized.rsplit("/", 1)[-1]
        blocked = (".env", "secret", "credential", ".pem", ".key")
        return not any(token in name for token in blocked)

    @staticmethod
    def _architecture_identity(stack: list[str], has_endpoints: bool, has_presentation: bool, infrastructure: list[str]) -> tuple[str, str]:
        if has_presentation and has_endpoints:
            system_type = "Full-stack web application"
            summary = "Full-stack application with a client presentation, API boundary, application behavior, and indexed supporting systems."
        elif has_endpoints:
            system_type = "Backend API application"
            summary = "Server-side API application with indexed endpoints and application components."
        elif has_presentation:
            system_type = "Frontend web application"
            summary = "Client-side web application with indexed presentation components."
        else:
            system_type = "Indexed codebase"
            summary = "The current index does not expose enough application boundaries for a complete system map."
        if infrastructure:
            summary = f"{summary} Confirmed supporting technologies: {', '.join(infrastructure)}."
        return system_type, summary

    @staticmethod
    def _endpoint_domain(endpoint_path: str, file_path: str) -> str:
        ignored = {"api", "v1", "v2", "v3"}
        segments = [segment.lower() for segment in endpoint_path.strip("/").split("/") if segment and not segment.startswith("{")]
        meaningful = [segment for segment in segments if segment not in ignored]
        domain = meaningful[0] if len(meaningful) > 1 else ""
        return RepositoryService._slug(domain or RepositoryService._path_domain(file_path, ("routes", "router")) or "application")

    @staticmethod
    def _path_domain(path: str, removable: tuple[str, ...]) -> str:
        stem = Path(path).stem.lower()
        for token in removable:
            stem = stem.replace(token, "")
        stem = stem.strip("_-")
        if stem and stem not in {"index", "main", "base"}:
            return RepositoryService._slug(stem)
        parts = [part.lower() for part in path.replace("\\", "/").split("/")[:-1]]
        return RepositoryService._slug(next((part for part in reversed(parts) if part not in removable and part not in {"app", "src", "backend"}), "application"))

    @staticmethod
    def _display_domain(domain: str) -> str:
        aliases = {"auth": "Authentication", "users": "User", "user": "User", "restaurants": "Restaurant", "restaurant": "Restaurant", "hotels": "Hotel", "hotel": "Hotel", "models": "Data"}
        return aliases.get(domain, domain.replace("_", " ").replace("-", " ").title())

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "application"

    def get_overview(self, repository_id: str) -> OverviewResponse:
        repository = self.get_indexed_repository(repository_id)
        return OverviewResponse(
            repository_id=repository.id,
            name=repository.name,
            detected_stack=self.detect_stack(repository),
            important_files=self.important_files(repository),
            modules=self.build_modules(repository),
            endpoints=[
                EndpointDTO(
                    endpoint_key=node_id("endpoint", f"{endpoint.method}:{endpoint.path}"),
                    method=endpoint.method,
                    path=endpoint.path,
                    handler=endpoint.handler,
                    file_path=endpoint.file_path,
                    start_line=endpoint.start_line,
                    end_line=endpoint.end_line,
                    metadata=endpoint.metadata,
                )
                for endpoint in repository.endpoints
            ],
            documentation_gaps=self.documentation_gaps(repository),
            architecture=self.build_architecture(repository),
            stats={
                "files": len(repository.files),
                "functions": len([symbol for symbol in repository.symbols if symbol.symbol_type in {"function", "method"}]),
                "classes": len([symbol for symbol in repository.symbols if symbol.symbol_type == "class"]),
                "endpoints": len(repository.endpoints),
                "chunks": len(repository.chunks),
                "graph_nodes": len(repository.graph_nodes),
            },
        )

    def get_reading_path(self, repository_id: str) -> ReadingPathResponse:
        repository = self.get_indexed_repository(repository_id)
        items: list[ReadingPathItemDTO] = []
        for file in self.important_files(repository)[:7]:
            signals = [ReadingPathSignalDTO(type="heuristic", detail=file.reason)]
            if Path(file.file_path).name.lower().startswith("readme"):
                title = "Project documentation"
                confidence = "high"
            elif Path(file.file_path).name.lower() in {"main.py", "app.py"}:
                title = "Application entrypoint"
                confidence = "high"
            elif "router" in file.file_path.lower() or "routes" in file.file_path.lower():
                title = "API routing file"
                confidence = "medium"
            else:
                title = "Important file"
                confidence = "medium"
            items.append(
                ReadingPathItemDTO(
                    rank=len(items) + 1,
                    file_path=file.file_path,
                    title=title,
                    reason=file.reason,
                    confidence=confidence,
                    signals=signals,
                )
            )
        return ReadingPathResponse(repository_id=repository.id, index_version=repository.current_index_version, items=items)

    def list_symbols(self, repository_id: str, query: str | None = None, symbol_type: str | None = None) -> SymbolListResponse:
        repository = self.get_indexed_repository(repository_id)
        normalized_query = (query or "").lower()
        items = []
        for symbol in repository.symbols:
            if normalized_query and normalized_query not in symbol.name.lower() and normalized_query not in symbol.file_path.lower():
                continue
            if symbol_type and symbol.symbol_type != symbol_type:
                continue
            items.append(
                SymbolDTO(
                    symbol_id=symbol.id,
                    file_path=symbol.file_path,
                    symbol_type=symbol.symbol_type,
                    name=symbol.name,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    signature=symbol.signature,
                    index_version=repository.current_index_version,
                )
            )
        return SymbolListResponse(items=items[:100])

    def list_endpoints(self, repository_id: str) -> EndpointListResponse:
        repository = self.get_indexed_repository(repository_id)
        return EndpointListResponse(
            items=[
                EndpointDTO(
                    endpoint_key=node_id("endpoint", f"{endpoint.method}:{endpoint.path}"),
                    method=endpoint.method,
                    path=endpoint.path,
                    handler=endpoint.handler,
                    file_path=endpoint.file_path,
                    start_line=endpoint.start_line,
                    end_line=endpoint.end_line,
                    metadata=endpoint.metadata,
                )
                for endpoint in repository.endpoints
            ]
        )

    def _delete_managed_storage(self, repository: RepositoryState) -> None:
        repository_root = (settings.repository_storage_dir / repository.id).resolve()
        storage_root = settings.repository_storage_dir.resolve()
        if repository_root.exists() and self._is_relative_to(repository_root, storage_root):
            shutil.rmtree(repository_root)

        if repository.source_type == "upload_zip" and repository.source_uri:
            upload_path = Path(repository.source_uri).resolve()
            upload_root = settings.upload_storage_dir.resolve()
            if upload_path.exists() and upload_path.is_file() and self._is_relative_to(upload_path, upload_root):
                upload_path.unlink()

    def _file_contains(self, path: Path, value: str) -> bool:
        try:
            return value in read_text(path).lower()
        except OSError:
            return False

    def _is_relative_to(self, path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
        except ValueError:
            return False
        return True
