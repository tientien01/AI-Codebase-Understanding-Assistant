from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from urllib.parse import quote

from app.services.code_analysis.models import (
    IRClass,
    IRFunction,
    IRModule,
    ReferenceArtifact,
    SourceSpan,
    canonical_symbol_key,
)


ALLOWED_NODE_TYPES = frozenset({"file", "function", "method", "class", "schema", "model"})
ALLOWED_RELATIONS = frozenset({"imports", "calls"})
INVERSE_RELATIONS = {"imported_by": "imports", "called_by": "calls"}
ALLOWED_ORIGINS = frozenset({"parser_exact", "resolver_exact", "framework_rule", "heuristic"})
ALLOWED_SUPPORT = frozenset({"source_exact", "static_resolved", "static_ambiguous", "heuristic_inferred"})


@dataclass(frozen=True)
class GraphCandidate:
    schema_version: str
    candidate_kind: str
    canonical_key: str
    repository_id: str
    index_version_id: str
    node_type: str | None
    label: str | None
    source_key: str | None
    target_key: str | None
    relation_type: str | None
    origin: str
    producer_name: str
    producer_version: str
    support_type: str
    source_spans: tuple[SourceSpan, ...]
    evidence_reference_key: str | None = None
    confidence: float | None = None
    status: str = "pending"
    normalization_reason: str | None = None


@dataclass(frozen=True)
class GraphValidationIssue:
    code: str
    severity: str
    candidate_key: str
    message_safe: str


@dataclass(frozen=True)
class GraphNormalizationPolicy:
    minimum_inferred_confidence: float = 0.0
    max_issues: int = 100

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_inferred_confidence <= 1.0:
            raise ValueError("minimum inferred confidence must be in [0, 1]")
        if self.max_issues < 1:
            raise ValueError("max issues must be positive")


@dataclass(frozen=True)
class NormalizedGraphArtifact:
    schema_version: str
    repository_id: str
    index_version_id: str
    candidates: tuple[GraphCandidate, ...]
    issues: tuple[GraphValidationIssue, ...]
    critical_issue_count: int

    @property
    def active_candidates(self) -> tuple[GraphCandidate, ...]:
        if self.critical_issue_count:
            return ()
        return tuple(item for item in self.candidates if item.status in {"accepted", "changed"})

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_edge_key(relation: str, source: str, target: str, discriminator: str) -> str:
    digest = hashlib.sha256(discriminator.encode("utf-8")).hexdigest()[:16]
    return f"edge:v1:{relation}:{quote(source, safe='')}:{quote(target, safe='')}:{digest}"


class ReferenceGraphCandidateBuilder:
    name = "python-reference-graph-builder"
    version = "1"

    def build(self, module: IRModule, references: ReferenceArtifact) -> tuple[GraphCandidate, ...]:
        candidates = self._module_nodes(module)
        for reference in references.references:
            if reference.outcome != "resolved":
                continue
            source_key = reference.source_entity_key or reference.source_file_key
            target_key = reference.target_keys[0]
            relation = "calls" if reference.reference_type == "call" else "imports"
            candidates.append(
                GraphCandidate(
                    schema_version="graph-candidate/v1",
                    candidate_kind="edge",
                    canonical_key=canonical_edge_key(relation, source_key, target_key, reference.canonical_key),
                    repository_id=reference.repository_id,
                    index_version_id=reference.index_version_id,
                    node_type=None,
                    label=None,
                    source_key=source_key,
                    target_key=target_key,
                    relation_type=relation,
                    origin="resolver_exact",
                    producer_name=self.name,
                    producer_version=self.version,
                    support_type="static_resolved",
                    source_spans=reference.source_spans,
                    evidence_reference_key=reference.canonical_key,
                )
            )
        return tuple(candidates)

    def _module_nodes(self, module: IRModule) -> list[GraphCandidate]:
        nodes: list[GraphCandidate] = []
        for function, kind in self._functions(module):
            key = canonical_symbol_key(module.file_key, function.qualified_name, kind)
            nodes.append(
                GraphCandidate(
                    schema_version="graph-candidate/v1",
                    candidate_kind="node",
                    canonical_key=key,
                    repository_id=module.repository_id,
                    index_version_id=module.index_version_id,
                    node_type=kind,
                    label=function.qualified_name,
                    source_key=None,
                    target_key=None,
                    relation_type=None,
                    origin="parser_exact",
                    producer_name=self.name,
                    producer_version=self.version,
                    support_type="source_exact",
                    source_spans=(SourceSpan(module.file_key, function.start_line, function.end_line, module.content_hash),),
                )
            )
        return nodes

    def _functions(self, module: IRModule) -> list[tuple[IRFunction, str]]:
        result = [(item, "function") for item in module.functions]
        for item in module.classes:
            result.extend(self._class_functions(item))
        return result

    def _class_functions(self, item: IRClass) -> list[tuple[IRFunction, str]]:
        result: list[tuple[IRFunction, str]] = []
        for child in item.body:
            if isinstance(child, IRFunction):
                result.append((child, "method"))
            elif isinstance(child, IRClass):
                result.extend(self._class_functions(child))
        return result


class GraphCandidateNormalizer:
    """Validate and normalize candidates into deterministic audited output."""

    def normalize(
        self,
        candidates: tuple[GraphCandidate, ...],
        *,
        repository_id: str,
        index_version_id: str,
        known_node_keys: frozenset[str],
        policy: GraphNormalizationPolicy | None = None,
    ) -> NormalizedGraphArtifact:
        active_policy = policy or GraphNormalizationPolicy()
        normalized: list[GraphCandidate] = []
        issues: list[GraphValidationIssue] = []
        seen: dict[str, GraphCandidate] = {}
        ordered = sorted(
            candidates,
            key=lambda item: (
                item.canonical_key,
                item.candidate_kind,
                item.origin,
                json.dumps(asdict(item), sort_keys=True, separators=(",", ":")),
            ),
        )

        for candidate in ordered:
            current, candidate_issues = self._normalize_one(
                candidate,
                repository_id,
                index_version_id,
                known_node_keys,
                active_policy,
            )
            issues.extend(candidate_issues)
            if current.status == "dropped":
                normalized.append(current)
                continue
            existing = seen.get(current.canonical_key)
            if existing is not None:
                if self._semantic_tuple(existing) == self._semantic_tuple(current):
                    normalized.append(replace(current, status="dropped", normalization_reason="exact_duplicate"))
                    issues.append(self._issue("duplicate_candidate", "warning", current, "Exact duplicate candidate was dropped."))
                else:
                    normalized.append(replace(current, status="dropped", normalization_reason="conflicting_key"))
                    issues.append(self._issue("conflicting_canonical_key", "critical", current, "Canonical candidate key has conflicting content."))
                continue
            seen[current.canonical_key] = current
            normalized.append(current)

        bounded_issues = tuple(sorted(issues, key=lambda item: (item.severity, item.code, item.candidate_key))[: active_policy.max_issues])
        output = tuple(sorted(normalized, key=lambda item: (item.canonical_key, item.status, item.normalization_reason or "")))
        return NormalizedGraphArtifact(
            schema_version="normalized-graph/v1",
            repository_id=repository_id,
            index_version_id=index_version_id,
            candidates=output,
            issues=bounded_issues,
            critical_issue_count=sum(item.severity == "critical" for item in issues),
        )

    def _normalize_one(
        self,
        candidate: GraphCandidate,
        repository_id: str,
        index_version_id: str,
        known_node_keys: frozenset[str],
        policy: GraphNormalizationPolicy,
    ) -> tuple[GraphCandidate, list[GraphValidationIssue]]:
        errors: list[GraphValidationIssue] = []
        if candidate.schema_version != "graph-candidate/v1":
            errors.append(self._issue("invalid_schema", "critical", candidate, "Candidate schema is invalid."))
        if candidate.repository_id != repository_id or candidate.index_version_id != index_version_id:
            errors.append(self._issue("ownership_mismatch", "critical", candidate, "Candidate ownership does not match the artifact."))
        if candidate.origin not in ALLOWED_ORIGINS or candidate.support_type not in ALLOWED_SUPPORT:
            errors.append(self._issue("invalid_provenance", "critical", candidate, "Candidate provenance is invalid."))
        if not candidate.producer_name or not candidate.producer_version or not candidate.source_spans:
            errors.append(self._issue("missing_provenance", "critical", candidate, "Candidate producer or source span is missing."))
        if candidate.origin == "heuristic":
            if candidate.confidence is None or not 0.0 <= candidate.confidence <= 1.0:
                errors.append(self._issue("invalid_inferred_confidence", "critical", candidate, "Inferred confidence must be in [0, 1]."))
            elif candidate.confidence < policy.minimum_inferred_confidence:
                errors.append(self._issue("inferred_confidence_below_policy", "critical", candidate, "Inferred candidate does not meet the declared policy."))

        current = candidate
        if candidate.candidate_kind == "node":
            if candidate.node_type not in ALLOWED_NODE_TYPES or not candidate.label or candidate.source_key or candidate.target_key or candidate.relation_type:
                errors.append(self._issue("invalid_node_shape", "critical", candidate, "Node candidate shape or type is invalid."))
            if not candidate.canonical_key.startswith(("file:v1:", "symbol:v1:")):
                errors.append(self._issue("invalid_canonical_key", "critical", candidate, "Node candidate key is not canonical."))
        elif candidate.candidate_kind == "edge":
            if not candidate.source_key or not candidate.target_key or not candidate.relation_type or candidate.node_type or candidate.label:
                errors.append(self._issue("invalid_edge_shape", "critical", candidate, "Edge candidate shape is invalid."))
            else:
                if not candidate.canonical_key.startswith("edge:v1:"):
                    errors.append(self._issue("invalid_canonical_key", "critical", candidate, "Edge candidate key is not canonical."))
                if candidate.relation_type in INVERSE_RELATIONS:
                    relation = INVERSE_RELATIONS[candidate.relation_type]
                    current = replace(
                        candidate,
                        canonical_key=canonical_edge_key(relation, candidate.target_key, candidate.source_key, candidate.canonical_key),
                        source_key=candidate.target_key,
                        target_key=candidate.source_key,
                        relation_type=relation,
                        status="changed",
                        normalization_reason="inverse_direction",
                    )
                elif candidate.relation_type not in ALLOWED_RELATIONS:
                    errors.append(self._issue("invalid_relation_type", "critical", candidate, "Edge relation type is invalid."))
                if candidate.source_key not in known_node_keys or candidate.target_key not in known_node_keys:
                    errors.append(self._issue("dangling_endpoint", "critical", candidate, "Edge endpoint is absent from the declared same-version catalog."))
                if not candidate.evidence_reference_key:
                    errors.append(self._issue("missing_edge_evidence", "critical", candidate, "Edge candidate lacks reference evidence."))
        else:
            errors.append(self._issue("invalid_candidate_kind", "critical", candidate, "Candidate kind is invalid."))

        if errors:
            return replace(current, status="dropped", normalization_reason=errors[0].code), errors
        if current.status == "pending":
            current = replace(current, status="accepted")
        return current, []

    def _semantic_tuple(self, item: GraphCandidate) -> tuple[object, ...]:
        return (
            item.candidate_kind,
            item.node_type,
            item.label,
            item.source_key,
            item.target_key,
            item.relation_type,
            item.origin,
            item.producer_name,
            item.producer_version,
            item.support_type,
            item.source_spans,
            item.evidence_reference_key,
            item.confidence,
        )

    def _issue(self, code: str, severity: str, candidate: GraphCandidate, message: str) -> GraphValidationIssue:
        return GraphValidationIssue(code, severity, candidate.canonical_key[:2048], message[:240])
