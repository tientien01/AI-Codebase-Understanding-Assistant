"""Exact canonical-output equivalence gate for full and incremental builds."""

from __future__ import annotations

from enum import StrEnum
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.artifacts.models import SHA256


class EquivalenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CanonicalFamily(StrEnum):
    FACTS = "facts"
    REFERENCES = "references"
    GRAPH_NODES = "graph_nodes"
    GRAPH_EDGES = "graph_edges"
    CHUNKS = "chunks"
    LEXICAL_STATE = "lexical_state"
    READINESS = "readiness"
    FINGERPRINTS = "fingerprints"
    BENCHMARK_ANSWERS = "benchmark_answers"


REQUIRED_FAMILIES = tuple(CanonicalFamily)


class CanonicalEntry(EquivalenceModel):
    canonical_key: str = Field(min_length=1, max_length=2048)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("canonical entry sha256 must be lowercase SHA-256")
        return value


class CanonicalFamilySnapshot(EquivalenceModel):
    family: CanonicalFamily
    entries: tuple[CanonicalEntry, ...]

    @model_validator(mode="after")
    def validate_unique_keys(self) -> "CanonicalFamilySnapshot":
        keys = [entry.canonical_key for entry in self.entries]
        if len(keys) != len(set(keys)):
            raise ValueError("canonical family entry keys must be unique")
        return self


class EquivalenceSnapshot(EquivalenceModel):
    schema_version: Literal["equivalence-snapshot/v1"] = "equivalence-snapshot/v1"
    repository_id: str = Field(pattern=r"^repo_[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
    target_snapshot_sha256: str
    configuration_sha256: str
    families: tuple[CanonicalFamilySnapshot, ...]

    @field_validator("target_snapshot_sha256", "configuration_sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if not SHA256.fullmatch(value):
            raise ValueError("equivalence identity must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_families(self) -> "EquivalenceSnapshot":
        families = [family.family for family in self.families]
        if len(families) != len(set(families)) or set(families) != set(
            REQUIRED_FAMILIES
        ):
            raise ValueError("equivalence snapshot must declare every family once")
        return self

    def canonical_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude_none=False)
        payload["families"] = sorted(
            payload["families"], key=lambda item: item["family"]
        )
        for family in payload["families"]:
            family["entries"] = sorted(
                family["entries"], key=lambda item: item["canonical_key"]
            )
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")


class MismatchKind(StrEnum):
    MISSING_FROM_FULL = "missing_from_full"
    MISSING_FROM_INCREMENTAL = "missing_from_incremental"
    DIGEST_MISMATCH = "digest_mismatch"


class EquivalenceMismatch(EquivalenceModel):
    family: CanonicalFamily
    canonical_key: str
    kind: MismatchKind
    full_sha256: str | None = None
    incremental_sha256: str | None = None


class EquivalenceResult(EquivalenceModel):
    equivalent: bool
    compared_entries: int = Field(ge=0)
    total_mismatches: int = Field(ge=0)
    mismatches: tuple[EquivalenceMismatch, ...]
    diagnostics_truncated: bool


class EquivalenceInputError(RuntimeError):
    pass


class EquivalenceService:
    def __init__(self, *, max_diagnostics: int) -> None:
        if max_diagnostics <= 0:
            raise ValueError("max_diagnostics must be positive")
        self.max_diagnostics = max_diagnostics

    def compare(
        self,
        full: EquivalenceSnapshot,
        incremental: EquivalenceSnapshot,
    ) -> EquivalenceResult:
        if (
            full.repository_id != incremental.repository_id
            or full.target_snapshot_sha256
            != incremental.target_snapshot_sha256
            or full.configuration_sha256 != incremental.configuration_sha256
        ):
            raise EquivalenceInputError(
                "Full and incremental outputs must describe the same target identity"
            )
        full_families = {family.family: family for family in full.families}
        incremental_families = {
            family.family: family for family in incremental.families
        }
        mismatches: list[EquivalenceMismatch] = []
        compared_entries = 0
        for family in REQUIRED_FAMILIES:
            full_entries = {
                item.canonical_key: item.sha256
                for item in full_families[family].entries
            }
            incremental_entries = {
                item.canonical_key: item.sha256
                for item in incremental_families[family].entries
            }
            for key in sorted(set(full_entries) | set(incremental_entries)):
                full_sha = full_entries.get(key)
                incremental_sha = incremental_entries.get(key)
                if full_sha is not None and incremental_sha is not None:
                    compared_entries += 1
                if full_sha == incremental_sha:
                    continue
                if full_sha is None:
                    kind = MismatchKind.MISSING_FROM_FULL
                elif incremental_sha is None:
                    kind = MismatchKind.MISSING_FROM_INCREMENTAL
                else:
                    kind = MismatchKind.DIGEST_MISMATCH
                mismatches.append(
                    EquivalenceMismatch(
                        family=family,
                        canonical_key=key,
                        kind=kind,
                        full_sha256=full_sha,
                        incremental_sha256=incremental_sha,
                    )
                )
        total = len(mismatches)
        return EquivalenceResult(
            equivalent=total == 0,
            compared_entries=compared_entries,
            total_mismatches=total,
            mismatches=tuple(mismatches[: self.max_diagnostics]),
            diagnostics_truncated=total > self.max_diagnostics,
        )
