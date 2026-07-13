"""Deterministic affected-set planning for safe incremental index builds."""

from __future__ import annotations

from enum import StrEnum
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.artifacts.models import SHA256


class PlannerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _validate_sha256(value: str, field_name: str) -> str:
    if not SHA256.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256")
    return value


def _validate_file_path(value: str) -> str:
    if not value or value.startswith("/") or "\\" in value or "\x00" in value:
        raise ValueError("file path must be a relative POSIX path")
    for part in value.split("/"):
        if part in {"", ".", ".."} or not re.fullmatch(
            r"[A-Za-z0-9._~%+@=-]+", part
        ):
            raise ValueError("file path contains an invalid segment")
        for match in re.finditer("%", part):
            encoded_octet = part[match.start() + 1 : match.start() + 3]
            if not re.fullmatch(r"[0-9A-Fa-f]{2}", encoded_octet):
                raise ValueError("file path contains invalid percent encoding")
    return value


def _validate_file_key(value: str) -> str:
    if not value.startswith("file:v1:") or len(value) <= len("file:v1:"):
        raise ValueError("file key must be canonical")
    _validate_file_path(value.removeprefix("file:v1:"))
    return value


class ComponentIdentity(PlannerModel):
    schema_version: Literal["incremental-components/v1"] = "incremental-components/v1"
    pipeline_version: str = Field(min_length=1, max_length=128)
    scan_schema_version: str = Field(min_length=1, max_length=128)
    parser_bundle_version: str = Field(min_length=1, max_length=128)
    resolver_rules_version: str = Field(min_length=1, max_length=128)
    framework_rules_version: str = Field(min_length=1, max_length=128)
    graph_schema_version: str = Field(min_length=1, max_length=128)
    normalizer_version: str = Field(min_length=1, max_length=128)
    chunker_version: str = Field(min_length=1, max_length=128)
    ranking_config_id: str = Field(min_length=1, max_length=128)
    security_policy_sha256: str
    configuration_sha256: str

    @field_validator("security_policy_sha256", "configuration_sha256")
    @classmethod
    def validate_checksum(cls, value: str, info) -> str:
        return _validate_sha256(value, info.field_name)


class FileFingerprint(PlannerModel):
    schema_version: Literal["file-fingerprint/v1"] = "file-fingerprint/v1"
    file_key: str
    path: str
    content_sha256: str
    normalized_sha256: str
    documentation_sha256: str
    structure_sha256: str
    public_api_sha256: str
    dependency_sha256: str
    byte_size: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _validate_file_path(value)

    @field_validator(
        "content_sha256",
        "normalized_sha256",
        "documentation_sha256",
        "structure_sha256",
        "public_api_sha256",
        "dependency_sha256",
    )
    @classmethod
    def validate_checksum(cls, value: str, info) -> str:
        return _validate_sha256(value, info.field_name)

    @model_validator(mode="after")
    def validate_file_identity(self) -> "FileFingerprint":
        if self.file_key != f"file:v1:{self.path}":
            raise ValueError("file key must be the canonical key for its path")
        return self


class DependencyRelation(StrEnum):
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    ENDPOINT_CHAIN = "endpoint_chain"
    FRONTEND_BACKEND = "frontend_backend"
    TEST_TARGET = "test_target"
    CONFIG_USAGE = "config_usage"
    SCHEMA_USAGE = "schema_usage"


class DependencyEdge(PlannerModel):
    source_file_key: str
    target_file_key: str
    relation: DependencyRelation

    @field_validator("source_file_key", "target_file_key")
    @classmethod
    def validate_file_key(cls, value: str) -> str:
        return _validate_file_key(value)

    @model_validator(mode="after")
    def reject_self_edge(self) -> "DependencyEdge":
        if self.source_file_key == self.target_file_key:
            raise ValueError("dependency edge cannot be self-referential")
        return self


class AffectedSetLimits(PlannerModel):
    max_affected_files: int = Field(gt=0)
    max_dependency_depth: int = Field(ge=0)
    max_repository_fraction: float = Field(gt=0, le=1)


class ChangeKind(StrEnum):
    ADDED = "added"
    DELETED = "deleted"
    MOVED = "moved"
    CONTENT = "content"
    DOCUMENTATION = "documentation"
    STRUCTURE = "structure"
    PUBLIC_API = "public_api"
    DEPENDENCY = "dependency"


CHANGE_ORDER = (
    ChangeKind.DOCUMENTATION,
    ChangeKind.STRUCTURE,
    ChangeKind.PUBLIC_API,
    ChangeKind.DEPENDENCY,
    ChangeKind.CONTENT,
)


class FileChange(PlannerModel):
    previous_file_key: str | None = None
    current_file_key: str | None = None
    kinds: tuple[ChangeKind, ...]

    @field_validator("previous_file_key", "current_file_key")
    @classmethod
    def validate_optional_file_key(cls, value: str | None) -> str | None:
        return _validate_file_key(value) if value is not None else None

    @model_validator(mode="after")
    def validate_shape(self) -> "FileChange":
        if not self.kinds or len(self.kinds) != len(set(self.kinds)):
            raise ValueError("file change kinds must be non-empty and unique")
        identity_kinds = {ChangeKind.ADDED, ChangeKind.DELETED, ChangeKind.MOVED}
        if identity_kinds.intersection(self.kinds) and len(self.kinds) != 1:
            raise ValueError("identity change kinds cannot be combined")
        if self.kinds == (ChangeKind.ADDED,) and (
            self.previous_file_key is not None or self.current_file_key is None
        ):
            raise ValueError("added change identity is invalid")
        if self.kinds == (ChangeKind.DELETED,) and (
            self.previous_file_key is None or self.current_file_key is not None
        ):
            raise ValueError("deleted change identity is invalid")
        if self.kinds == (ChangeKind.MOVED,) and (
            self.previous_file_key is None or self.current_file_key is None
        ):
            raise ValueError("moved change requires old and new identities")
        if not identity_kinds.intersection(self.kinds) and (
            self.previous_file_key is None
            or self.previous_file_key != self.current_file_key
        ):
            raise ValueError("fingerprint changes require one stable file identity")
        return self


class MoveCandidate(PlannerModel):
    previous_file_key: str
    current_file_key: str
    content_sha256: str
    method: Literal["exact_unique_content"] = "exact_unique_content"

    @field_validator("previous_file_key", "current_file_key")
    @classmethod
    def validate_file_key(cls, value: str) -> str:
        return _validate_file_key(value)

    @field_validator("content_sha256")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        return _validate_sha256(value, "content_sha256")


class IncrementalMode(StrEnum):
    INCREMENTAL = "incremental"
    FULL = "full"


class FallbackReason(StrEnum):
    COMPONENT_INCOMPATIBLE = "component_incompatible"
    AMBIGUOUS_MOVE = "ambiguous_move"
    DEPENDENCY_GRAPH_INVALID = "dependency_graph_invalid"
    AFFECTED_FILE_LIMIT = "affected_file_limit"
    DEPENDENCY_DEPTH_LIMIT = "dependency_depth_limit"
    AFFECTED_FRACTION_LIMIT = "affected_fraction_limit"


class IncrementalPlan(PlannerModel):
    schema_version: Literal["incremental-plan/v1"] = "incremental-plan/v1"
    mode: IncrementalMode
    reasons: tuple[FallbackReason, ...]
    changes: tuple[FileChange, ...]
    move_candidates: tuple[MoveCandidate, ...]
    rebuild_file_keys: tuple[str, ...]
    reuse_file_keys: tuple[str, ...]
    deleted_file_keys: tuple[str, ...]

    @model_validator(mode="after")
    def validate_plan_sets(self) -> "IncrementalPlan":
        groups = (
            self.rebuild_file_keys,
            self.reuse_file_keys,
            self.deleted_file_keys,
        )
        if any(tuple(sorted(group)) != group or len(group) != len(set(group)) for group in groups):
            raise ValueError("plan file-key sets must be sorted and unique")
        rebuild, reuse, deleted = map(set, groups)
        if rebuild & reuse or rebuild & deleted or reuse & deleted:
            raise ValueError("plan file-key sets must not overlap")
        if self.mode is IncrementalMode.FULL:
            if not self.reasons or self.reuse_file_keys:
                raise ValueError("full plan requires reasons and cannot reuse files")
        elif self.reasons:
            raise ValueError("incremental plan cannot contain fallback reasons")
        return self

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


class IncrementalPlanner:
    def plan(
        self,
        *,
        previous_files: tuple[FileFingerprint, ...],
        current_files: tuple[FileFingerprint, ...],
        previous_components: ComponentIdentity,
        current_components: ComponentIdentity,
        dependencies: tuple[DependencyEdge, ...],
        limits: AffectedSetLimits,
    ) -> IncrementalPlan:
        previous = self._index_snapshot(previous_files)
        current = self._index_snapshot(current_files)
        changes, moves, ambiguous_move = self._classify(previous, current)
        deleted_keys = tuple(sorted(set(previous) - set(current)))

        if previous_components != current_components:
            return self._full_plan(
                current, changes, moves, deleted_keys, FallbackReason.COMPONENT_INCOMPATIBLE
            )
        if ambiguous_move:
            return self._full_plan(
                current, changes, moves, deleted_keys, FallbackReason.AMBIGUOUS_MOVE
            )
        known_keys = set(previous) | set(current)
        edge_identities = {
            (edge.source_file_key, edge.target_file_key, edge.relation)
            for edge in dependencies
        }
        if len(edge_identities) != len(dependencies) or any(
            edge.source_file_key not in known_keys
            or edge.target_file_key not in known_keys
            for edge in dependencies
        ):
            return self._full_plan(
                current,
                changes,
                moves,
                deleted_keys,
                FallbackReason.DEPENDENCY_GRAPH_INVALID,
            )

        reverse_dependencies: dict[str, set[str]] = {}
        for edge in sorted(
            dependencies,
            key=lambda item: (
                item.target_file_key,
                item.source_file_key,
                item.relation.value,
            ),
        ):
            reverse_dependencies.setdefault(edge.target_file_key, set()).add(
                edge.source_file_key
            )

        changed_current = {
            change.current_file_key
            for change in changes
            if change.current_file_key is not None
        }
        frontier = sorted(
            {
                key
                for change in changes
                for key in (change.previous_file_key, change.current_file_key)
                if key is not None
            }
        )
        affected = set(changed_current)
        depth_by_key = {key: 0 for key in frontier}
        cursor = 0
        while cursor < len(frontier):
            target = frontier[cursor]
            cursor += 1
            depth = depth_by_key[target]
            for dependent in sorted(reverse_dependencies.get(target, ())):
                if dependent not in current or dependent in affected:
                    continue
                next_depth = depth + 1
                if next_depth > limits.max_dependency_depth:
                    return self._full_plan(
                        current,
                        changes,
                        moves,
                        deleted_keys,
                        FallbackReason.DEPENDENCY_DEPTH_LIMIT,
                    )
                affected.add(dependent)
                depth_by_key[dependent] = next_depth
                frontier.append(dependent)
                if len(affected) > limits.max_affected_files:
                    return self._full_plan(
                        current,
                        changes,
                        moves,
                        deleted_keys,
                        FallbackReason.AFFECTED_FILE_LIMIT,
                    )

        if len(affected) > limits.max_affected_files:
            return self._full_plan(
                current,
                changes,
                moves,
                deleted_keys,
                FallbackReason.AFFECTED_FILE_LIMIT,
            )
        fraction = len(affected) / max(1, len(current))
        if fraction > limits.max_repository_fraction:
            return self._full_plan(
                current,
                changes,
                moves,
                deleted_keys,
                FallbackReason.AFFECTED_FRACTION_LIMIT,
            )
        reusable = tuple(sorted(set(current) - affected))
        return IncrementalPlan(
            mode=IncrementalMode.INCREMENTAL,
            reasons=(),
            changes=changes,
            move_candidates=moves,
            rebuild_file_keys=tuple(sorted(affected)),
            reuse_file_keys=reusable,
            deleted_file_keys=deleted_keys,
        )

    def _index_snapshot(
        self, files: tuple[FileFingerprint, ...]
    ) -> dict[str, FileFingerprint]:
        by_key = {item.file_key: item for item in files}
        if len(by_key) != len(files) or len({item.path for item in files}) != len(files):
            raise ValueError("snapshot file keys and paths must be unique")
        return by_key

    def _classify(
        self,
        previous: dict[str, FileFingerprint],
        current: dict[str, FileFingerprint],
    ) -> tuple[tuple[FileChange, ...], tuple[MoveCandidate, ...], bool]:
        changes: list[FileChange] = []
        added = set(current) - set(previous)
        deleted = set(previous) - set(current)
        for key in sorted(set(previous) & set(current)):
            before, after = previous[key], current[key]
            kinds = self._changed_dimensions(before, after)
            if kinds:
                changes.append(
                    FileChange(
                        previous_file_key=key,
                        current_file_key=key,
                        kinds=kinds,
                    )
                )

        deleted_by_hash: dict[str, list[str]] = {}
        added_by_hash: dict[str, list[str]] = {}
        for key in deleted:
            deleted_by_hash.setdefault(previous[key].content_sha256, []).append(key)
        for key in added:
            added_by_hash.setdefault(current[key].content_sha256, []).append(key)
        moves: list[MoveCandidate] = []
        moved_old: set[str] = set()
        moved_new: set[str] = set()
        ambiguous = False
        for digest in sorted(set(deleted_by_hash) & set(added_by_hash)):
            old_keys = sorted(deleted_by_hash[digest])
            new_keys = sorted(added_by_hash[digest])
            if len(old_keys) == len(new_keys) == 1:
                moves.append(
                    MoveCandidate(
                        previous_file_key=old_keys[0],
                        current_file_key=new_keys[0],
                        content_sha256=digest,
                    )
                )
                changes.append(
                    FileChange(
                        previous_file_key=old_keys[0],
                        current_file_key=new_keys[0],
                        kinds=(ChangeKind.MOVED,),
                    )
                )
                moved_old.add(old_keys[0])
                moved_new.add(new_keys[0])
            else:
                ambiguous = True
        changes.extend(
            FileChange(current_file_key=key, kinds=(ChangeKind.ADDED,))
            for key in sorted(added - moved_new)
        )
        changes.extend(
            FileChange(previous_file_key=key, kinds=(ChangeKind.DELETED,))
            for key in sorted(deleted - moved_old)
        )
        return (
            tuple(
                sorted(
                    changes,
                    key=lambda item: (
                        item.current_file_key or "",
                        item.previous_file_key or "",
                        tuple(kind.value for kind in item.kinds),
                    ),
                )
            ),
            tuple(moves),
            ambiguous,
        )

    def _changed_dimensions(
        self, before: FileFingerprint, after: FileFingerprint
    ) -> tuple[ChangeKind, ...]:
        dimensions = {
            ChangeKind.DOCUMENTATION: before.documentation_sha256
            != after.documentation_sha256,
            ChangeKind.STRUCTURE: before.structure_sha256 != after.structure_sha256,
            ChangeKind.PUBLIC_API: before.public_api_sha256 != after.public_api_sha256,
            ChangeKind.DEPENDENCY: before.dependency_sha256 != after.dependency_sha256,
        }
        kinds = [kind for kind in CHANGE_ORDER if dimensions.get(kind, False)]
        if (
            before.content_sha256 != after.content_sha256
            or before.normalized_sha256 != after.normalized_sha256
            or before.byte_size != after.byte_size
        ) and not kinds:
            kinds.append(ChangeKind.CONTENT)
        return tuple(kinds)

    def _full_plan(
        self,
        current: dict[str, FileFingerprint],
        changes: tuple[FileChange, ...],
        moves: tuple[MoveCandidate, ...],
        deleted_keys: tuple[str, ...],
        reason: FallbackReason,
    ) -> IncrementalPlan:
        return IncrementalPlan(
            mode=IncrementalMode.FULL,
            reasons=(reason,),
            changes=changes,
            move_candidates=moves,
            rebuild_file_keys=tuple(sorted(current)),
            reuse_file_keys=(),
            deleted_file_keys=deleted_keys,
        )
