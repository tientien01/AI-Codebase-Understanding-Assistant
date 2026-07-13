"""Typed contracts for deterministic, resumable indexing phases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Callable, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.artifacts.models import SHA256
from app.services.artifacts.store import (
    ArtifactStoreError,
    validate_logical_key,
    version_root_key,
)


class IndexPhase(StrEnum):
    PREFLIGHT = "preflight"
    SCAN = "scan"
    PARSE = "parse"
    RESOLVE = "resolve"
    GRAPH_CANDIDATES = "graph_candidates"
    NORMALIZE = "normalize"
    VALIDATE = "validate"
    RETRIEVAL_BUILD = "retrieval_build"
    OPTIONAL_VIEWS = "optional_views"
    FINGERPRINT = "fingerprint"


CANONICAL_PHASE_ORDER = tuple(IndexPhase)


class PhaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PhaseResourcePolicy(PhaseModel):
    max_seconds: int = Field(gt=0)
    max_memory_mb: int = Field(gt=0)
    max_items: int = Field(gt=0)
    max_workers: int = Field(gt=0)


class PhaseArtifact(PhaseModel):
    artifact_type: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    schema_version: str = Field(min_length=1, max_length=128)
    key: str
    sha256: str
    byte_size: int = Field(ge=0)
    records: int = Field(ge=0)

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        try:
            return validate_logical_key(value)
        except ArtifactStoreError:
            raise ValueError("artifact key must be a safe logical key") from None

    @field_validator("sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("artifact sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_type_scope(self) -> "PhaseArtifact":
        if f"/artifacts/{self.artifact_type}/" not in self.key:
            raise ValueError("artifact key must be scoped by its artifact type")
        return self

    def identity_payload(self) -> dict[str, str | int]:
        return self.model_dump(mode="json")


class PhaseInput(PhaseModel):
    schema_version: Literal["phase-input/v1"] = "phase-input/v1"
    repository_id: str
    index_version_id: str
    phase: IndexPhase
    phase_version: str = Field(min_length=1, max_length=128)
    configuration_sha256: str
    artifacts: tuple[PhaseArtifact, ...]
    resource_policy: PhaseResourcePolicy

    @field_validator("repository_id")
    @classmethod
    def validate_repository_id(cls, value: str) -> str:
        try:
            version_root_key(value, "idx_validation")
        except ArtifactStoreError:
            raise ValueError("repository_id must be an opaque repository ID") from None
        return value

    @field_validator("index_version_id")
    @classmethod
    def validate_index_version_id(cls, value: str) -> str:
        try:
            version_root_key("repo_validation", value)
        except ArtifactStoreError:
            raise ValueError("index_version_id must be an opaque index-version ID") from None
        return value

    @field_validator("configuration_sha256")
    @classmethod
    def validate_configuration_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("configuration_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_artifact_ownership(self) -> "PhaseInput":
        root = f"{version_root_key(self.repository_id, self.index_version_id)}/"
        if any(not artifact.key.startswith(root) for artifact in self.artifacts):
            raise ValueError("phase input artifact has incompatible ownership")
        types = [artifact.artifact_type for artifact in self.artifacts]
        if len(types) != len(set(types)):
            raise ValueError("phase input artifact types must be unique")
        return self

    def idempotency_key(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "repository_id": self.repository_id,
            "index_version_id": self.index_version_id,
            "phase": self.phase.value,
            "phase_version": self.phase_version,
            "configuration_sha256": self.configuration_sha256,
            "resource_policy": self.resource_policy.model_dump(mode="json"),
            "artifacts": [artifact.identity_payload() for artifact in self.artifacts],
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class PhaseOutput(PhaseModel):
    schema_version: Literal["phase-output/v1"] = "phase-output/v1"
    phase: IndexPhase
    artifacts: tuple[PhaseArtifact, ...]

    @model_validator(mode="after")
    def validate_unique_artifact_types(self) -> "PhaseOutput":
        types = [artifact.artifact_type for artifact in self.artifacts]
        if len(types) != len(set(types)):
            raise ValueError("phase output artifact types must be unique")
        return self


class PhaseCheckpoint(PhaseModel):
    schema_version: Literal["phase-checkpoint/v1"] = "phase-checkpoint/v1"
    repository_id: str
    index_version_id: str
    phase: IndexPhase
    phase_version: str
    idempotency_key: str
    configuration_sha256: str
    output: PhaseOutput

    @field_validator("idempotency_key", "configuration_sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("checkpoint identity must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_phase(self) -> "PhaseCheckpoint":
        if self.output.phase != self.phase:
            raise ValueError("checkpoint output phase does not match checkpoint phase")
        root = f"{version_root_key(self.repository_id, self.index_version_id)}/"
        if any(not artifact.key.startswith(root) for artifact in self.output.artifacts):
            raise ValueError("checkpoint output artifact has incompatible ownership")
        return self

    def canonical_bytes(self) -> bytes:
        payload = self.model_dump(mode="json")
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")


class CheckpointReference(PhaseModel):
    phase: IndexPhase
    key: str
    sha256: str
    byte_size: int = Field(ge=0)

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        try:
            return validate_logical_key(value)
        except ArtifactStoreError:
            raise ValueError("checkpoint key must be a safe logical key") from None

    @field_validator("sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("checkpoint sha256 must be lowercase SHA-256")
        return value


@dataclass(frozen=True)
class PhaseExecutionContext:
    is_cancelled: Callable[[], bool]
    report_progress: Callable[[IndexPhase, int], None] = lambda _phase, _percent: None

    def check_cancelled(self) -> None:
        if self.is_cancelled():
            raise PhaseCancelledError("Index phase execution was cancelled")

    def progress(self, phase: IndexPhase, percent: int) -> None:
        if not 0 <= percent <= 100:
            raise ValueError("phase progress must be between 0 and 100")
        self.report_progress(phase, percent)


class IndexPhaseDefinition(Protocol):
    phase: IndexPhase
    version: str
    required_input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    resource_policy: PhaseResourcePolicy

    def execute(
        self, phase_input: PhaseInput, context: PhaseExecutionContext
    ) -> PhaseOutput: ...


class PhasePipelineError(RuntimeError):
    """Stable pipeline failure containing logical phase identity only."""


class InvalidPhaseRegistryError(PhasePipelineError):
    pass


class PhaseInputError(PhasePipelineError):
    pass


class PhaseOutputError(PhasePipelineError):
    pass


class PhaseCancelledError(PhasePipelineError):
    pass


class PhaseFailureKind(StrEnum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class PhaseFailure(RuntimeError):
    """Expected stage failure classification without transport details."""

    def __init__(self, kind: PhaseFailureKind) -> None:
        self.kind = kind
        super().__init__(kind.value)


class PhaseExecutionError(PhasePipelineError):
    def __init__(self, phase: IndexPhase, kind: PhaseFailureKind) -> None:
        self.phase = phase
        self.kind = kind
        self.retryable = kind is PhaseFailureKind.TRANSIENT
        super().__init__(f"Index phase {phase.value} failed ({kind.value})")
