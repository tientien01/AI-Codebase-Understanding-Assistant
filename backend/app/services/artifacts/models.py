"""Typed production v1 index-manifest contract."""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_TYPE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def _validate_prefixed_id(value: str, prefix: str) -> str:
    suffix = value.removeprefix(prefix)
    if not value.startswith(prefix) or not OPAQUE_ID.fullmatch(suffix):
        raise ValueError(f"value must be an opaque {prefix} identifier")
    return value


def validate_relative_uri(value: str) -> str:
    """Validate a portable storage URI without resolving a host path."""
    if not value or "\\" in value or "\x00" in value or value.startswith("/"):
        raise ValueError("URI must be a non-empty relative POSIX path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("URI contains an invalid path segment")
    return value


class ManifestModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True, strict=True
    )


class ManifestSource(ManifestModel):
    type: str = Field(min_length=1, max_length=64)
    revision: str | None = Field(default=None, max_length=512)
    snapshot_sha256: str

    @field_validator("snapshot_sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("snapshot_sha256 must be lowercase SHA-256")
        return value


class ManifestPipeline(ManifestModel):
    version: str = Field(min_length=1, max_length=128)
    configuration_sha256: str

    @field_validator("configuration_sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("configuration_sha256 must be lowercase SHA-256")
        return value


class ManifestArtifact(ManifestModel):
    type: str
    schema_version: str = Field(min_length=1, max_length=128)
    uri: str
    sha256: str
    byte_size: int = Field(alias="bytes", ge=0)
    records: int = Field(ge=0)
    required: bool

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if not ARTIFACT_TYPE.fullmatch(value):
            raise ValueError("artifact type must be a lowercase stable identifier")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("artifact sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_uri_scope(self) -> "ManifestArtifact":
        validate_relative_uri(self.uri)
        parts = self.uri.split("/")
        if len(parts) < 3 or parts[:2] != ["artifacts", self.type]:
            raise ValueError("artifact URI must be scoped by its artifact type")
        return self


class ManifestValidation(ManifestModel):
    status: Literal["passed", "passed_with_warnings", "failed"]
    report_uri: str
    report_sha256: str
    critical_issues: int = Field(ge=0)

    @field_validator("report_uri")
    @classmethod
    def validate_report_uri(cls, value: str) -> str:
        validate_relative_uri(value)
        if not value.startswith("artifacts/validation_report/"):
            raise ValueError("validation report URI must use validation_report scope")
        return value

    @field_validator("report_sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("report_sha256 must be lowercase SHA-256")
        return value


class ManifestTimestamps(ManifestModel):
    started_at: datetime
    finished_at: datetime

    @model_validator(mode="after")
    def validate_timestamps(self) -> "ManifestTimestamps":
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None:
            raise ValueError("manifest timestamps must include a timezone")
        if self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        return self


class IndexManifest(ManifestModel):
    schema_version: Literal["index-manifest/v1"]
    repository_id: str
    index_version_id: str
    sequence: int = Field(gt=0)
    base_index_version_id: str | None = None
    build_kind: Literal["full", "incremental"]
    source: ManifestSource
    pipeline: ManifestPipeline
    status: Literal[
        "building",
        "validating",
        "ready",
        "ready_with_warnings",
        "failed",
        "cancelled",
    ]
    artifacts: tuple[ManifestArtifact, ...]
    capabilities: dict[str, Any]
    coverage: dict[str, Any]
    validation: ManifestValidation
    timestamps: ManifestTimestamps

    @field_validator("repository_id")
    @classmethod
    def validate_repository_id(cls, value: str) -> str:
        return _validate_prefixed_id(value, "repo_")

    @field_validator("index_version_id", "base_index_version_id")
    @classmethod
    def validate_index_version_id(cls, value: str | None) -> str | None:
        return None if value is None else _validate_prefixed_id(value, "idx_")

    @model_validator(mode="after")
    def validate_manifest_identity(self) -> "IndexManifest":
        if self.base_index_version_id == self.index_version_id:
            raise ValueError("base index version must differ from the candidate")
        identities = [(item.type, item.uri) for item in self.artifacts]
        if len(identities) != len(set(identities)):
            raise ValueError("manifest artifact entries must be unique")
        if self.status == "ready" and self.validation.status != "passed":
            raise ValueError("ready manifest requires passed validation")
        if (
            self.status == "ready_with_warnings"
            and self.validation.status != "passed_with_warnings"
        ):
            raise ValueError(
                "ready_with_warnings manifest requires warning validation status"
            )
        if self.status in {"ready", "ready_with_warnings"} and self.validation.critical_issues:
            raise ValueError("ready manifest cannot contain critical issues")
        return self

    def canonical_bytes(self) -> bytes:
        """Return deterministic bytes used for manifest checksum identity."""
        payload = self.model_dump(mode="json", by_alias=True, exclude_none=False)
        return json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
