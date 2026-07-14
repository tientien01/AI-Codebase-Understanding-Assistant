from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from app.schemas.exploration import (
    ArchitectureComponentDTO,
    ArchitectureEvidenceDTO,
    ArchitectureFlowDTO,
    ArchitectureFlowStepDTO,
    ArchitectureOverviewDTO,
    ArchitectureRelationDTO,
)
from app.services.architecture.detectors import FrameworkAwareDetector, display_domain, endpoint_domain, layer_order
from app.services.architecture.models import ComponentCandidate, IndexedFileSignal, TechnologySignal
from app.services.index_models import RepositoryState
from app.services.text_utils import read_text


MAX_FILES = 600
MAX_FILE_CHARS = 128_000
DETECTOR_VERSION = "rule-based/v2"


class RuleBasedArchitectureEngine:
    """Build an explainable architecture projection from indexed repository facts."""

    def __init__(self, detector: FrameworkAwareDetector | None = None) -> None:
        self.detector = detector or FrameworkAwareDetector()

    def build(self, repository: RepositoryState, detected_stack: list[str] | None = None) -> ArchitectureOverviewDTO:
        files = self._collect_signals(repository)
        frameworks = self.detector.detect_frameworks(files)
        technologies = sorted(set((detected_stack or []) + frameworks))
        candidates = self.detector.classify_files(files)
        technology_sources = self.detector.detect_technologies(files)
        components = self._build_components(repository, candidates, frameworks, technology_sources)
        relations, relation_unknowns = self._build_relations(repository, components, technology_sources)
        flows = self._build_flows(repository, components, relations)
        style, style_reason = self._select_style(files, components, repository)
        system_type, summary = self._identity(style, frameworks, technology_sources)

        unknowns = relation_unknowns
        if not repository.graph_edges:
            unknowns.append("Cross-component graph evidence is unavailable; convention-based relations remain inferred.")
        if not any(component.kind == "api" for component in components) and style not in {"library", "cli"}:
            unknowns.append("No API boundary was detected from indexed endpoints or framework markers.")
        if not any(component.kind in {"api", "application"} for component in components):
            unknowns.append("No API or application-service boundary was detected.")
        if style == "package_map":
            unknowns.append("No supported architecture style crossed the deterministic evidence threshold.")

        return ArchitectureOverviewDTO(
            style=style,
            style_reason=style_reason,
            detector_version=DETECTOR_VERSION,
            system_type=system_type,
            summary=summary,
            technologies=sorted(set(technologies + [signal.label for signal in technology_sources]))[:12],
            components=components[:28],
            relations=relations[:40],
            primary_flows=flows[:3],
            coverage_state="ready" if style != "package_map" and len(components) >= 3 else "limited",
            unknowns=sorted(set(unknowns))[:8],
        )

    def detect_frameworks(self, repository: RepositoryState) -> list[str]:
        return self.detector.detect_frameworks(self._collect_signals(repository))

    @staticmethod
    def _collect_signals(repository: RepositoryState) -> list[IndexedFileSignal]:
        signals: list[IndexedFileSignal] = []
        for file in sorted(repository.files, key=lambda item: item.path)[:MAX_FILES]:
            if not _safe_source(file.path) or file.file_type not in {"source", "config"}:
                continue
            try:
                content = read_text(file.absolute_path)[:MAX_FILE_CHARS]
            except OSError:
                content = ""
            signals.append(IndexedFileSignal(path=file.path, language=file.language, content=content))
        return signals

    def _build_components(
        self,
        repository: RepositoryState,
        candidates: list[ComponentCandidate],
        frameworks: list[str],
        technology_sources: dict[TechnologySignal, list[str]],
    ) -> list[ArchitectureComponentDTO]:
        components: list[ArchitectureComponentDTO] = []
        presentation_files = sorted({path for item in candidates if item.role == "presentation" for path in item.files})
        if presentation_files:
            components.extend([
                self._component("actor:user", "User", "actor", "actor", "actor", "Uses an indexed presentation surface.", [], "inferred", [self._evidence("framework_rule", "Presentation surface detected.", presentation_files[0])]),
                self._component("presentation:web", _presentation_label(frameworks), "presentation", "presentation", "presentation", "Client-facing presentation boundary.", presentation_files, "confirmed"),
            ])

        endpoint_groups: dict[str, list] = defaultdict(list)
        for endpoint in repository.endpoints:
            endpoint_groups[endpoint_domain(endpoint.path, endpoint.file_path)].append(endpoint)
        for domain in sorted(endpoint_groups)[:8]:
            endpoints = endpoint_groups[domain]
            label = "Operational Endpoints" if domain == "operational" else f"{display_domain(domain)} API"
            components.append(self._component(
                f"api:{domain}", label, "api", "api", "operational" if domain == "operational" else "api",
                f"Owns {len(endpoints)} indexed endpoint{'s' if len(endpoints) != 1 else ''}.",
                sorted({endpoint.file_path for endpoint in endpoints}), "confirmed", [
                    self._evidence("endpoint", f"{endpoint.method} {endpoint.path}", endpoint.file_path) for endpoint in endpoints[:6]
                ], endpoint_count=len(endpoints),
            ))

        endpoint_files = {endpoint.file_path for endpoint in repository.endpoints}
        for candidate in candidates:
            if candidate.role == "presentation":
                continue
            files = sorted(set(candidate.files))
            if candidate.role == "api" and set(files) <= endpoint_files:
                continue
            component_id = f"{candidate.kind}:{candidate.domain}"
            if any(item.id == component_id for item in components):
                continue
            support = "confirmed" if any("indexed source marker" in detail for _, detail in candidate.evidence) else "inferred"
            components.append(self._component(
                component_id,
                _component_label(candidate),
                candidate.kind,
                candidate.layer,
                candidate.role,
                _component_summary(candidate),
                files,
                support,
                [self._evidence("framework_rule" if "marker" in detail else "path_rule", detail, path) for path, detail in candidate.evidence[:6]],
            ))

        application_kinds = {"presentation", "api", "application", "domain", "data_access", "messaging", "external_adapter"}
        if not any(item.kind in application_kinds for item in components):
            package_groups: dict[str, list[str]] = defaultdict(list)
            for file in repository.files:
                if file.file_type != "source":
                    continue
                parts = file.path.replace("\\", "/").split("/")
                package = parts[0] if len(parts) > 1 else "root"
                package_groups[package].append(file.path)
            for package, paths in sorted(package_groups.items())[:8]:
                components.append(self._component(
                    f"module:{package}", f"{display_domain(package)} Package", "module", "package", "package",
                    f"Fallback package grouping for {len(paths)} indexed source file{'s' if len(paths) != 1 else ''}.",
                    paths, "inferred", [self._evidence("path_rule", "Package boundary from indexed relative paths.", paths[0])],
                ))

        backend_children = [item for item in components if item.kind in {"api", "application", "domain", "data_access", "messaging", "external_adapter"}]
        if backend_children:
            backend_technology = next((name for name in ("FastAPI", "Spring Boot", "ASP.NET Core", "NestJS", "Express", "Django", "Flask", "Go HTTP") if name in frameworks), None)
            components.append(self._component(
                "container:backend", f"{backend_technology} Backend" if backend_technology else "Application Backend",
                "container", "container", "backend_container", "Server-side application boundary.",
                sorted({path for item in backend_children for path in item.file_paths}), "confirmed" if backend_technology else "inferred",
                [self._evidence("framework_rule", f"Detected backend framework: {backend_technology}.") ] if backend_technology else [],
                technology=backend_technology,
            ))

        for signal, paths in sorted(technology_sources.items(), key=lambda item: item[0].label):
            components.append(self._component(
                f"infrastructure:{signal.key}", signal.label, "infrastructure", "infrastructure", signal.category,
                f"Detected from {len(paths)} indexed source or dependency file{'s' if len(paths) != 1 else ''}.",
                paths, "confirmed", [self._evidence("technology_marker", f"{signal.label} marker detected.", path) for path in paths[:4]],
                technology=signal.category,
            ))

        return sorted(components, key=lambda item: (_component_order(item), item.label, item.id))

    def _build_relations(
        self,
        repository: RepositoryState,
        components: list[ArchitectureComponentDTO],
        technology_sources: dict[TechnologySignal, list[str]],
    ) -> tuple[list[ArchitectureRelationDTO], list[str]]:
        by_id = {component.id: component for component in components}
        relations: dict[tuple[str, str, str], ArchitectureRelationDTO] = {}
        unknowns: list[str] = []

        def add(source: str, target: str, label: str, support: str, evidence: list[ArchitectureEvidenceDTO]) -> None:
            if source == target or source not in by_id or target not in by_id:
                return
            key = (source, target, label)
            existing = relations.get(key)
            if existing is None or _support_rank(support) < _support_rank(existing.support):
                relations[key] = ArchitectureRelationDTO(source=source, target=target, label=label, support=support, evidence=evidence[:6])

        if "actor:user" in by_id and "presentation:web" in by_id:
            add("actor:user", "presentation:web", "uses", "inferred", by_id["presentation:web"].evidence)

        owners: dict[str, str] = {}
        for component in components:
            if component.kind in {"actor", "container", "infrastructure"}:
                continue
            for path in component.file_paths:
                owners.setdefault(path, component.id)
        node_by_id = {node.id: node for node in repository.graph_nodes}
        labels = {
            "calls_api": "HTTP / JSON", "exposes_endpoint": "routes to", "calls": "calls", "imports": "imports",
            "depends_on": "depends on", "reads": "reads from", "writes": "writes to", "implements": "implements",
            "publishes": "publishes", "consumes": "consumes",
        }
        for edge in sorted(repository.graph_edges, key=lambda item: (item.source, item.target, item.type)):
            source_node = node_by_id.get(edge.source)
            target_node = node_by_id.get(edge.target)
            source = owners.get(source_node.file_path) if source_node and source_node.file_path else None
            target = owners.get(target_node.file_path) if target_node and target_node.file_path else None
            if not source or not target or edge.type.lower() in {"contains", "defined_in"}:
                continue
            support = "confirmed" if edge.evidence_level != "inferred" and edge.confidence >= 0.75 else "inferred"
            add(source, target, labels.get(edge.type.lower(), edge.type.replace("_", " ").lower()), support, [
                self._evidence("graph_edge", f"{edge.type} ({edge.confidence:.2f})", source_node.file_path)
            ])

        if "presentation:web" in by_id and "container:backend" in by_id:
            add("presentation:web", "container:backend", "HTTP / JSON", "inferred", by_id["presentation:web"].evidence)

        self._add_convention_relations(components, add)

        for signal, marker_paths in technology_sources.items():
            target = f"infrastructure:{signal.key}"
            if target not in by_id:
                continue
            eligible = [
                component for component in components
                if component.kind not in {"actor", "presentation", "container", "api", "infrastructure"}
                and set(component.file_paths).intersection(marker_paths)
            ]
            preferred_roles = {"database": "data_access", "cache": "data_access", "vector_store": "data_access", "message_broker": "messaging", "external_api": "external_adapter", "object_store": "data_access"}
            owner = next((item for item in eligible if item.kind == preferred_roles.get(signal.category)), eligible[0] if eligible else None)
            if owner:
                add(owner.id, target, signal.relation_label, "confirmed", by_id[target].evidence)
            else:
                unknowns.append(f"{signal.label} was detected, but its owning component could not be confirmed.")

        ordered = sorted(relations.values(), key=lambda item: (_support_rank(item.support), item.source, item.target, item.label))
        return ordered, unknowns

    @staticmethod
    def _add_convention_relations(components: list[ArchitectureComponentDTO], add) -> None:
        layers = defaultdict(list)
        for component in components:
            layers[component.kind].append(component)
        pairs = (("api", "application", "calls"), ("application", "domain", "uses"), ("application", "data_access", "reads / writes"), ("domain", "data_access", "uses"))
        for source_kind, target_kind, label in pairs:
            for source in layers[source_kind]:
                if source.role == "operational":
                    continue
                domain = source.id.split(":", 1)[-1]
                target = next((item for item in layers[target_kind] if item.id.endswith(f":{domain}")), None)
                if target is None and len(layers[target_kind]) == 1:
                    target = layers[target_kind][0]
                if target:
                    add(source.id, target.id, label, "inferred", source.evidence + target.evidence)

    def _build_flows(self, repository: RepositoryState, components: list[ArchitectureComponentDTO], relations: list[ArchitectureRelationDTO]) -> list[ArchitectureFlowDTO]:
        by_id = {component.id: component for component in components}
        outgoing: dict[str, list[ArchitectureRelationDTO]] = defaultdict(list)
        for relation in relations:
            outgoing[relation.source].append(relation)
        for values in outgoing.values():
            values.sort(key=lambda item: (_support_rank(item.support), _component_order(by_id[item.target]), item.target))

        grouped: dict[str, list] = defaultdict(list)
        for endpoint in repository.endpoints:
            domain = endpoint_domain(endpoint.path, endpoint.file_path)
            if domain != "operational":
                grouped[domain].append(endpoint)
        flows: list[ArchitectureFlowDTO] = []
        for domain in sorted(grouped)[:3]:
            endpoint = sorted(grouped[domain], key=lambda item: (item.path, item.method))[0]
            start = f"api:{domain}"
            if start not in by_id:
                continue
            steps = []
            if "presentation:web" in by_id:
                steps.append(ArchitectureFlowStepDTO(component_id="presentation:web", label=by_id["presentation:web"].label, support="inferred"))
            steps.append(ArchitectureFlowStepDTO(component_id=start, label=by_id[start].label, support="confirmed"))
            current = start
            visited = {start, "presentation:web", "container:backend"}
            while len(steps) < 6:
                relation = next((item for item in outgoing.get(current, []) if item.target not in visited and by_id[item.target].role != "operational"), None)
                if relation is None:
                    break
                visited.add(relation.target)
                steps.append(ArchitectureFlowStepDTO(component_id=relation.target, label=by_id[relation.target].label, support=relation.support))
                current = relation.target
            flow_parts = [part for part in endpoint.path.strip("/").split("/") if part and part.lower() not in {"api", "v1", "v2", "v3"} and not part.startswith("{")]
            flow_name = display_domain(flow_parts[-1] if flow_parts else domain)
            flows.append(ArchitectureFlowDTO(
                id=f"flow:{endpoint.method.lower()}:{endpoint.path.strip('/').replace('/', '-') or 'root'}",
                label=f"{flow_name} flow", summary=f"{endpoint.method} {endpoint.path}", steps=steps,
                evidence=[self._evidence("endpoint", f"{endpoint.method} {endpoint.path}", endpoint.file_path)],
            ))
        return flows

    @staticmethod
    def _select_style(files: list[IndexedFileSignal], components: list[ArchitectureComponentDTO], repository: RepositoryState) -> tuple[str, str]:
        kinds = {item.kind for item in components}
        all_content = "\n".join(file.content.lower() for file in files)
        all_paths = [file.normalized_path for file in files]
        if "messaging" in kinds and any(item.role == "message_broker" for item in components):
            return "event_driven", "Messaging handlers and a broker dependency were detected."
        if "presentation" in kinds and "api" in kinds:
            return "layered_web", "A presentation boundary and indexed HTTP API were detected."
        if any("/views/" in f"/{path}" for path in all_paths) and any("/controllers/" in f"/{path}" for path in all_paths) and any("/models/" in f"/{path}" for path in all_paths):
            return "mvc", "View, controller and model conventions were detected."
        if "api" in kinds:
            domains = {item.id.split(":", 1)[-1] for item in components if item.kind == "api" and item.role != "operational"}
            if len(domains) >= 3 and "application" in kinds:
                return "modular", "Several API domains with application components were detected."
            return "backend_api", "An indexed server API boundary was detected without a presentation container."
        if any(marker in all_content for marker in ("argparse", "click.command", "commander", "cobra.command", "system.commandline")):
            return "cli", "Command-line entrypoint markers were detected."
        if any(Path(path).name.lower() in {"lib.rs", "setup.py", "pyproject.toml", "package.json", "go.mod", "pom.xml"} for path in all_paths) and not repository.endpoints:
            return "library", "A package manifest/public entrypoint was detected without an application API."
        return "package_map", "Only package/file grouping signals were available."

    @staticmethod
    def _identity(style: str, frameworks: list[str], technologies: dict[TechnologySignal, list[str]]) -> tuple[str, str]:
        names = {
            "layered_web": "Full-stack web application", "backend_api": "Backend API application", "mvc": "MVC application",
            "modular": "Modular application", "event_driven": "Event-driven application", "library": "Library or SDK",
            "cli": "Command-line application", "package_map": "Indexed codebase",
        }
        system_type = names[style]
        framework_text = f" using {', '.join(frameworks[:3])}" if frameworks else ""
        support_text = f" Supporting systems: {', '.join(signal.label for signal in technologies)}." if technologies else ""
        return system_type, f"Deterministic {system_type.lower()} view{framework_text}.{support_text}"

    @staticmethod
    def _component(
        component_id: str, label: str, kind: str, layer: str, role: str, summary: str, paths: list[str], support: str,
        evidence: list[ArchitectureEvidenceDTO] | None = None, endpoint_count: int = 0, technology: str | None = None,
    ) -> ArchitectureComponentDTO:
        return ArchitectureComponentDTO(
            id=component_id, label=label, kind=kind, layer=layer, role=role, support=support, summary=summary,
            technology=technology, file_paths=sorted(set(paths))[:20], endpoint_count=endpoint_count, evidence=(evidence or [])[:8],
        )

    @staticmethod
    def _evidence(kind: str, detail: str, file_path: str | None = None) -> ArchitectureEvidenceDTO:
        return ArchitectureEvidenceDTO(type=kind, detail=detail, file_path=file_path)


def _safe_source(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    segments = [segment for segment in normalized.split("/") if segment]
    name = segments[-1] if segments else ""
    blocked_segments = {".git", "node_modules", "venv", ".venv", "dist", "build", "secrets", "credentials"}
    if any(segment in blocked_segments for segment in segments[:-1]):
        return False
    return not (
        name.startswith(".env")
        or any(token in name for token in ("secret", "credential"))
        or Path(name).suffix in {".pem", ".key", ".p12", ".pfx"}
    )


def _presentation_label(frameworks: list[str]) -> str:
    if "Next.js" in frameworks:
        return "Next.js Web App"
    if "React" in frameworks:
        return "React Web App"
    return "Web Interface"


def _component_label(candidate: ComponentCandidate) -> str:
    name = display_domain(candidate.domain)
    suffix = {
        "api": "API", "application": "Service", "domain": "Domain", "data_access": "Repository",
        "messaging": "Worker", "external_adapter": "Integration", "entrypoint": "Entrypoint",
    }.get(candidate.role, "Component")
    if candidate.role == "data_model":
        return "Data Models" if candidate.domain in {"application", "data", "models"} else f"{name} Models"
    return f"{name} {suffix}"


def _component_summary(candidate: ComponentCandidate) -> str:
    descriptions = {
        "api": "Framework-detected request boundary", "application": "Application orchestration and use-case behavior",
        "domain": "Domain entities and business rules", "data_access": "Persistence and storage boundary",
        "data_model": "Indexed data model and schema definitions", "messaging": "Background or message-driven processing",
        "external_adapter": "External system integration boundary", "entrypoint": "Executable application entrypoint",
    }
    return f"{descriptions.get(candidate.role, 'Indexed component')} represented by {len(set(candidate.files))} source file{'s' if len(set(candidate.files)) != 1 else ''}."


def _component_order(component: ArchitectureComponentDTO) -> int:
    if component.kind == "actor":
        return -2
    if component.kind == "container":
        return -1
    if component.kind == "infrastructure":
        return 10
    return layer_order(component.layer)


def _support_rank(support: str) -> int:
    return {"confirmed": 0, "inferred": 1, "unknown": 2}.get(support, 3)
