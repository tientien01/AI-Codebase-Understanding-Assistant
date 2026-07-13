from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.indexing.validation_service import CapabilityReadiness


class ReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ArtifactEvidence(ReadinessModel):
    artifact_type: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    state: Literal["ready", "missing", "failed", "stale"]


class CapabilitySpec(ReadinessModel):
    capability: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,127}$")
    mandatory: bool
    required_artifact_types: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    requires_provider: bool = False

    @field_validator("required_artifact_types", "dependencies")
    @classmethod
    def normalize_unique_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("capability declarations must be unique")
        return tuple(sorted(values))


class CapabilityEvidence(ReadinessModel):
    capability: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,127}$")
    artifacts: tuple[ArtifactEvidence, ...]
    total_units: int = Field(ge=0)
    successful_units: int = Field(ge=0)
    unresolved_references: int = Field(default=0, ge=0)
    critical_issue_ids: tuple[str, ...] = ()
    source_freshness: Literal["fresh", "stale"] = "fresh"
    supported: bool = True
    provider_available: bool = True

    @field_validator("artifacts")
    @classmethod
    def normalize_artifacts(cls, values: tuple[ArtifactEvidence, ...]) -> tuple[ArtifactEvidence, ...]:
        names = [item.artifact_type for item in values]
        if len(names) != len(set(names)):
            raise ValueError("artifact evidence must be unique")
        return tuple(sorted(values, key=lambda item: item.artifact_type))

    @field_validator("critical_issue_ids")
    @classmethod
    def normalize_issue_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("critical issue IDs must be unique")
        return tuple(sorted(values))

    @model_validator(mode="after")
    def validate_counts(self) -> "CapabilityEvidence":
        if self.successful_units > self.total_units:
            raise ValueError("successful units cannot exceed total units")
        if self.unresolved_references > self.total_units:
            raise ValueError("unresolved references cannot exceed total units")
        return self


class CapabilityReadinessReport(ReadinessModel):
    schema_version: Literal["capability-readiness/v1"]
    repository_id: str = Field(min_length=1, max_length=128)
    index_version_id: str = Field(min_length=1, max_length=128)
    readiness: tuple[CapabilityReadiness, ...]
    mandatory_capabilities: tuple[str, ...]
    activation_allowed: bool
    manifest_capabilities: dict[str, dict[str, object]]

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class CapabilityReadinessCalculator:
    ACTIVATABLE_STATES = frozenset({"ready", "limited"})

    def calculate(
        self,
        *,
        repository_id: str,
        index_version_id: str,
        specs: tuple[CapabilitySpec, ...],
        evidence: tuple[CapabilityEvidence, ...],
    ) -> CapabilityReadinessReport:
        specs_by_name = self._unique_map(specs, "spec")
        evidence_by_name = self._unique_map(evidence, "evidence")
        if set(specs_by_name) != set(evidence_by_name):
            raise ValueError("capability spec and evidence sets must match")
        order = self._dependency_order(specs_by_name)
        readiness_by_name: dict[str, CapabilityReadiness] = {}

        for name in order:
            spec = specs_by_name[name]
            item = evidence_by_name[name]
            state, reasons = self._base_state(spec, item)
            state, reasons = self._apply_dependencies(state, reasons, spec, readiness_by_name)
            coverage = self._coverage(item)
            readiness_by_name[name] = CapabilityReadiness(
                id=self._readiness_id(repository_id, index_version_id, name),
                capability=name,
                state=state,
                reason_codes=tuple(sorted(set(reasons))),
                required_artifact_types=spec.required_artifact_types,
                validation_issue_id=item.critical_issue_ids[0] if item.critical_issue_ids else None,
                coverage=coverage,
                remediation=self._remediation(state, reasons),
            )

        readiness = tuple(readiness_by_name[name] for name in sorted(readiness_by_name))
        mandatory = tuple(sorted(spec.capability for spec in specs if spec.mandatory))
        activation_allowed = all(readiness_by_name[name].state in self.ACTIVATABLE_STATES for name in mandatory)
        manifest_capabilities = {
            item.capability: {"state": item.state, "coverage": item.coverage}
            for item in readiness
        }
        return CapabilityReadinessReport(
            schema_version="capability-readiness/v1",
            repository_id=repository_id,
            index_version_id=index_version_id,
            readiness=readiness,
            mandatory_capabilities=mandatory,
            activation_allowed=activation_allowed,
            manifest_capabilities=manifest_capabilities,
        )

    def _unique_map(self, values, label: str):
        result = {item.capability: item for item in values}
        if len(result) != len(values):
            raise ValueError(f"duplicate capability {label}")
        return result

    def _dependency_order(self, specs: dict[str, CapabilitySpec]) -> tuple[str, ...]:
        visiting: set[str] = set()
        visited: set[str] = set()
        order: list[str] = []

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError("capability dependency cycle")
            if name in visited:
                return
            visiting.add(name)
            for dependency in specs[name].dependencies:
                if dependency not in specs:
                    raise ValueError(f"unknown capability dependency: {dependency}")
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            order.append(name)

        for name in sorted(specs):
            visit(name)
        return tuple(order)

    def _base_state(self, spec: CapabilitySpec, item: CapabilityEvidence) -> tuple[str, list[str]]:
        artifact_states = {artifact.artifact_type: artifact.state for artifact in item.artifacts}
        required_states = [artifact_states.get(name, "missing") for name in spec.required_artifact_types]
        if item.source_freshness == "stale" or "stale" in required_states:
            return "stale", ["SOURCE_OR_ARTIFACT_STALE"]
        if item.critical_issue_ids:
            return "failed", ["CRITICAL_VALIDATION_ISSUE"]
        if "failed" in required_states:
            return "failed", ["REQUIRED_ARTIFACT_FAILED"]
        if "missing" in required_states:
            return "unavailable", ["REQUIRED_ARTIFACT_MISSING"]
        if not item.supported:
            return "unavailable", ["CAPABILITY_UNSUPPORTED"]
        if spec.requires_provider and not item.provider_available:
            return "unavailable", ["OPTIONAL_PROVIDER_UNAVAILABLE"]
        if item.total_units == 0:
            return "unavailable", ["NO_ELIGIBLE_INPUT"]
        if item.successful_units == 0:
            return "failed", ["PROFILE_PROCESSING_FAILED"]
        reasons: list[str] = []
        if item.successful_units < item.total_units:
            reasons.append("PARTIAL_COVERAGE")
        if item.unresolved_references:
            reasons.append("UNRESOLVED_REFERENCES_PRESENT")
        return ("limited", reasons) if reasons else ("ready", [])

    def _apply_dependencies(
        self,
        state: str,
        reasons: list[str],
        spec: CapabilitySpec,
        readiness: dict[str, CapabilityReadiness],
    ) -> tuple[str, list[str]]:
        if state in {"failed", "unavailable", "stale"}:
            return state, reasons
        dependency_states = [readiness[name].state for name in spec.dependencies]
        if "stale" in dependency_states:
            return "stale", [*reasons, "DEPENDENCY_STALE"]
        if "failed" in dependency_states:
            return "unavailable", [*reasons, "DEPENDENCY_FAILED"]
        if "unavailable" in dependency_states:
            return "unavailable", [*reasons, "DEPENDENCY_UNAVAILABLE"]
        if "limited" in dependency_states:
            return "limited", [*reasons, "DEPENDENCY_LIMITED"]
        return state, reasons

    def _coverage(self, item: CapabilityEvidence) -> dict[str, object]:
        fraction = round(item.successful_units / item.total_units, 6) if item.total_units else 0.0
        return {
            "total_units": item.total_units,
            "successful_units": item.successful_units,
            "failed_units": item.total_units - item.successful_units,
            "unresolved_references": item.unresolved_references,
            "success_fraction": fraction,
        }

    def _readiness_id(self, repository_id: str, index_version_id: str, capability: str) -> str:
        digest = hashlib.sha256(f"{repository_id}|{index_version_id}|{capability}".encode("utf-8")).hexdigest()[:24]
        return f"capability_{digest}"

    def _remediation(self, state: str, reasons: list[str]) -> str | None:
        if state == "ready":
            return None
        reason = sorted(reasons)[0] if reasons else state.upper()
        return f"Resolve {reason.lower().replace('_', ' ')} and rebuild the candidate."
