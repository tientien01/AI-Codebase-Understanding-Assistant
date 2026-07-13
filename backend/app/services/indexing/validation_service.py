"""Deterministic candidate validation before immutable publication and activation."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.artifacts.models import IndexManifest
from app.services.artifacts.store import version_root_key


class ValidationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ValidationIssue(ValidationModel):
    id: str = Field(pattern=r"^issue_[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    severity: Literal["info", "warning", "error", "critical"]
    message_safe: str = Field(min_length=1, max_length=512)
    entity_type: str | None = Field(default=None, max_length=64)
    entity_key: str | None = Field(default=None, max_length=512)
    file_key: str | None = Field(default=None, max_length=1024)
    start_line: int | None = Field(default=None, gt=0)
    end_line: int | None = Field(default=None, gt=0)
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_range(self) -> "ValidationIssue":
        if (self.start_line is None) != (self.end_line is None):
            raise ValueError("validation source range must be complete")
        if self.start_line is not None and self.end_line < self.start_line:
            raise ValueError("validation source range is reversed")
        return self


class CapabilityReadiness(ValidationModel):
    id: str = Field(pattern=r"^capability_[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
    capability: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,127}$")
    state: Literal["ready", "limited", "unavailable", "failed", "stale"]
    reason_codes: tuple[str, ...] = ()
    required_artifact_types: tuple[str, ...]
    validation_issue_id: str | None = None
    coverage: dict[str, Any] = Field(default_factory=dict)
    remediation: str | None = Field(default=None, max_length=512)

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)) or any(
            not value or len(value) > 128 for value in values
        ):
            raise ValueError("capability reason codes must be unique stable values")
        return values

    @field_validator("required_artifact_types")
    @classmethod
    def validate_artifact_types(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("required artifact types must be unique")
        for value in values:
            if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value):
                raise ValueError("required artifact type is invalid")
        return values


class ValidatedCandidate(ValidationModel):
    manifest: IndexManifest
    issues: tuple[ValidationIssue, ...]
    capabilities: tuple[CapabilityReadiness, ...]
    mandatory_capabilities: tuple[str, ...]


class CandidateValidationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class CandidateValidator:
    ACTIVATABLE_STATUSES = {"ready", "ready_with_warnings"}
    MANDATORY_STATES = {"ready", "limited"}

    def validate(
        self,
        manifest: IndexManifest,
        issues: tuple[ValidationIssue, ...],
        capabilities: tuple[CapabilityReadiness, ...],
        mandatory_capabilities: tuple[str, ...],
    ) -> ValidatedCandidate:
        if manifest.status not in self.ACTIVATABLE_STATUSES:
            self._fail("MANIFEST_NOT_READY", "Candidate manifest is not ready")
        if len(mandatory_capabilities) != len(set(mandatory_capabilities)):
            self._fail(
                "DUPLICATE_MANDATORY_CAPABILITY",
                "Mandatory capability declarations are duplicated",
            )
        issue_ids = {issue.id for issue in issues}
        if len(issue_ids) != len(issues):
            self._fail("DUPLICATE_VALIDATION_ISSUE", "Validation issue IDs are duplicated")
        critical_count = sum(issue.severity == "critical" for issue in issues)
        if critical_count or manifest.validation.critical_issues:
            self._fail("CRITICAL_VALIDATION_ISSUE", "Candidate has critical validation issues")
        if manifest.validation.critical_issues != critical_count:
            self._fail(
                "VALIDATION_SUMMARY_MISMATCH",
                "Manifest validation summary does not match declared issues",
            )
        has_warning = any(issue.severity in {"warning", "error"} for issue in issues)
        expected_validation = "passed_with_warnings" if has_warning else "passed"
        if manifest.validation.status != expected_validation:
            self._fail(
                "VALIDATION_SUMMARY_MISMATCH",
                "Manifest validation status does not match declared issues",
            )
        by_capability = {item.capability: item for item in capabilities}
        if len(by_capability) != len(capabilities):
            self._fail("DUPLICATE_CAPABILITY", "Capability readiness is duplicated")
        if set(manifest.capabilities) != set(by_capability):
            self._fail(
                "CAPABILITY_SUMMARY_MISMATCH",
                "Manifest capabilities do not match readiness records",
            )
        artifact_types = {artifact.type for artifact in manifest.artifacts}
        required_artifact_types = {
            artifact.type for artifact in manifest.artifacts if artifact.required
        }
        for capability in capabilities:
            if capability.validation_issue_id not in {None, *issue_ids}:
                self._fail(
                    "UNKNOWN_VALIDATION_ISSUE",
                    "Capability references an unknown validation issue",
                )
            missing_types = set(capability.required_artifact_types) - artifact_types
            if missing_types:
                self._fail(
                    "MISSING_REQUIRED_ARTIFACT",
                    f"Capability {capability.capability} is missing a required artifact",
                )
            manifest_capability = manifest.capabilities.get(capability.capability)
            if not isinstance(manifest_capability, dict) or (
                manifest_capability.get("state") != capability.state
            ):
                self._fail(
                    "CAPABILITY_SUMMARY_MISMATCH",
                    f"Capability {capability.capability} does not match the manifest",
                )
        for capability_name in mandatory_capabilities:
            readiness = by_capability.get(capability_name)
            if readiness is None or readiness.state not in self.MANDATORY_STATES:
                self._fail(
                    "MANDATORY_CAPABILITY_NOT_READY",
                    f"Mandatory capability {capability_name} is not activatable",
                )
            if set(readiness.required_artifact_types) - required_artifact_types:
                self._fail(
                    "MANDATORY_ARTIFACT_NOT_REQUIRED",
                    f"Mandatory capability {capability_name} has an optional artifact declaration",
                )
        return ValidatedCandidate(
            manifest=manifest,
            issues=issues,
            capabilities=capabilities,
            mandatory_capabilities=mandatory_capabilities,
        )

    def _fail(self, code: str, message: str) -> None:
        raise CandidateValidationError(code, message)


def artifact_storage_key(manifest: IndexManifest, relative_uri: str) -> str:
    """Bind a manifest-relative URI to the candidate's opaque version root."""
    return (
        f"{version_root_key(manifest.repository_id, manifest.index_version_id)}/"
        f"{relative_uri}"
    )
