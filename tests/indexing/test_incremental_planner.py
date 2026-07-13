from __future__ import annotations

import hashlib

from pydantic import ValidationError
import pytest

from app.services.indexing.incremental_planner import (
    AffectedSetLimits,
    ChangeKind,
    ComponentIdentity,
    DependencyEdge,
    DependencyRelation,
    FallbackReason,
    FileChange,
    FileFingerprint,
    IncrementalMode,
    IncrementalPlanner,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _file(path: str, **updates) -> FileFingerprint:
    values = {
        "file_key": f"file:v1:{path}",
        "path": path,
        "content_sha256": _sha(f"{path}:content"),
        "normalized_sha256": _sha(f"{path}:normalized"),
        "documentation_sha256": _sha(f"{path}:docs"),
        "structure_sha256": _sha(f"{path}:structure"),
        "public_api_sha256": _sha(f"{path}:api"),
        "dependency_sha256": _sha(f"{path}:deps"),
        "byte_size": 100,
    }
    values.update(updates)
    return FileFingerprint(**values)


def _components(**updates) -> ComponentIdentity:
    values = {
        "pipeline_version": "pipeline/v1",
        "scan_schema_version": "scan/v1",
        "parser_bundle_version": "parsers/v1",
        "resolver_rules_version": "resolver/v1",
        "framework_rules_version": "framework/v1",
        "graph_schema_version": "graph/v1",
        "normalizer_version": "normalizer/v1",
        "chunker_version": "chunker/v1",
        "ranking_config_id": "ranking/v1",
        "security_policy_sha256": "a" * 64,
        "configuration_sha256": "b" * 64,
    }
    values.update(updates)
    return ComponentIdentity(**values)


def _limits(**updates) -> AffectedSetLimits:
    values = {
        "max_affected_files": 100,
        "max_dependency_depth": 10,
        "max_repository_fraction": 1.0,
    }
    values.update(updates)
    return AffectedSetLimits(**values)


def _plan(previous, current, *, dependencies=(), limits=None, previous_components=None, current_components=None):
    return IncrementalPlanner().plan(
        previous_files=tuple(previous),
        current_files=tuple(current),
        previous_components=previous_components or _components(),
        current_components=current_components or _components(),
        dependencies=tuple(dependencies),
        limits=limits or _limits(),
    )


def test_change_matrix_classifies_add_delete_and_fingerprint_dimensions() -> None:
    unchanged = _file("src/unchanged.py")
    body = _file("src/body.py")
    docs = _file("src/docs.py")
    structure = _file("src/structure.py")
    public_api = _file("src/api.py")
    dependency = _file("src/dependency.py")
    deleted = _file("src/deleted.py")
    added = _file("src/added.py")
    current = (
        unchanged,
        body.model_copy(
            update={
                "content_sha256": _sha("body:new"),
                "normalized_sha256": _sha("body:normalized:new"),
            }
        ),
        docs.model_copy(
            update={
                "content_sha256": _sha("docs:new"),
                "documentation_sha256": _sha("docs:fingerprint:new"),
            }
        ),
        structure.model_copy(
            update={
                "content_sha256": _sha("structure:new"),
                "structure_sha256": _sha("structure:fingerprint:new"),
            }
        ),
        public_api.model_copy(
            update={
                "content_sha256": _sha("api:new"),
                "public_api_sha256": _sha("api:fingerprint:new"),
            }
        ),
        dependency.model_copy(
            update={
                "content_sha256": _sha("dependency:new"),
                "dependency_sha256": _sha("dependency:fingerprint:new"),
            }
        ),
        added,
    )
    plan = _plan(
        (unchanged, body, docs, structure, public_api, dependency, deleted),
        current,
    )
    assert plan.mode is IncrementalMode.INCREMENTAL
    by_key = {
        change.current_file_key or change.previous_file_key: change.kinds
        for change in plan.changes
    }
    assert by_key[body.file_key] == (ChangeKind.CONTENT,)
    assert by_key[docs.file_key] == (ChangeKind.DOCUMENTATION,)
    assert by_key[structure.file_key] == (ChangeKind.STRUCTURE,)
    assert by_key[public_api.file_key] == (ChangeKind.PUBLIC_API,)
    assert by_key[dependency.file_key] == (ChangeKind.DEPENDENCY,)
    assert by_key[added.file_key] == (ChangeKind.ADDED,)
    assert by_key[deleted.file_key] == (ChangeKind.DELETED,)
    assert plan.reuse_file_keys == (unchanged.file_key,)
    assert plan.deleted_file_keys == (deleted.file_key,)


def test_exact_unique_move_is_a_candidate_but_ambiguous_move_falls_back() -> None:
    old = _file("old/name.py")
    new = _file(
        "new/name.py",
        content_sha256=old.content_sha256,
        normalized_sha256=old.normalized_sha256,
        documentation_sha256=old.documentation_sha256,
        structure_sha256=old.structure_sha256,
        public_api_sha256=old.public_api_sha256,
        dependency_sha256=old.dependency_sha256,
    )
    moved = _plan((old,), (new,))
    assert moved.mode is IncrementalMode.INCREMENTAL
    assert moved.changes[0].kinds == (ChangeKind.MOVED,)
    assert moved.move_candidates[0].previous_file_key == old.file_key
    assert moved.rebuild_file_keys == (new.file_key,)
    assert moved.deleted_file_keys == (old.file_key,)

    duplicate = old.model_copy(
        update={"file_key": "file:v1:old/copy.py", "path": "old/copy.py"}
    )
    ambiguous = _plan((old, duplicate), (new,))
    assert ambiguous.mode is IncrementalMode.FULL
    assert ambiguous.reasons == (FallbackReason.AMBIGUOUS_MOVE,)
    assert ambiguous.reuse_file_keys == ()


def test_component_incompatibility_forces_full_without_reuse() -> None:
    file = _file("src/app.py")
    plan = _plan(
        (file,),
        (file,),
        current_components=_components(parser_bundle_version="parsers/v2"),
    )
    assert plan.mode is IncrementalMode.FULL
    assert plan.reasons == (FallbackReason.COMPONENT_INCOMPATIBLE,)
    assert plan.rebuild_file_keys == (file.file_key,)
    assert plan.reuse_file_keys == ()


def test_reverse_dependency_expansion_is_typed_bounded_and_deterministic() -> None:
    target = _file("src/target.py")
    dependent = _file("src/dependent.py")
    transitive = _file("tests/test_dependent.py")
    spare = _file("src/spare.py")
    changed_target = target.model_copy(
        update={"content_sha256": _sha("target:new")}
    )
    edges = (
        DependencyEdge(
            source_file_key=dependent.file_key,
            target_file_key=target.file_key,
            relation=DependencyRelation.IMPORTS,
        ),
        DependencyEdge(
            source_file_key=transitive.file_key,
            target_file_key=dependent.file_key,
            relation=DependencyRelation.TEST_TARGET,
        ),
    )
    plan = _plan(
        (target, dependent, transitive, spare),
        (changed_target, dependent, transitive, spare),
        dependencies=tuple(reversed(edges)),
    )
    assert plan.rebuild_file_keys == tuple(
        sorted((target.file_key, dependent.file_key, transitive.file_key))
    )
    assert plan.reuse_file_keys == (spare.file_key,)
    reordered = _plan(
        (spare, transitive, dependent, target),
        (spare, transitive, dependent, changed_target),
        dependencies=edges,
    )
    assert reordered.canonical_bytes() == plan.canonical_bytes()

    depth_limited = _plan(
        (target, dependent, transitive, spare),
        (changed_target, dependent, transitive, spare),
        dependencies=edges,
        limits=_limits(max_dependency_depth=1),
    )
    assert depth_limited.reasons == (FallbackReason.DEPENDENCY_DEPTH_LIMIT,)
    file_limited = _plan(
        (target, dependent, transitive, spare),
        (changed_target, dependent, transitive, spare),
        dependencies=edges,
        limits=_limits(max_affected_files=2),
    )
    assert file_limited.reasons == (FallbackReason.AFFECTED_FILE_LIMIT,)
    fraction_limited = _plan(
        (target, dependent, transitive, spare),
        (changed_target, dependent, transitive, spare),
        dependencies=edges,
        limits=_limits(max_repository_fraction=0.5),
    )
    assert fraction_limited.reasons == (FallbackReason.AFFECTED_FRACTION_LIMIT,)


def test_unknown_dependency_endpoint_forces_full_and_invalid_inputs_fail() -> None:
    file = _file("src/app.py")
    invalid_edge = DependencyEdge(
        source_file_key=file.file_key,
        target_file_key="file:v1:src/missing.py",
        relation=DependencyRelation.CALLS,
    )
    plan = _plan((file,), (file,), dependencies=(invalid_edge,))
    assert plan.mode is IncrementalMode.FULL
    assert plan.reasons == (FallbackReason.DEPENDENCY_GRAPH_INVALID,)
    duplicate_edges = _plan(
        (file,), (file,), dependencies=(invalid_edge, invalid_edge)
    )
    assert duplicate_edges.reasons == (FallbackReason.DEPENDENCY_GRAPH_INVALID,)
    with pytest.raises(ValueError, match="unique"):
        _plan((file, file), (file,))
    with pytest.raises(ValidationError, match="canonical"):
        _file("src/app.py", file_key="file:v1:src/other.py")
    with pytest.raises(ValidationError, match="relative POSIX"):
        _file("C:\\source.py")
    with pytest.raises(ValidationError, match="invalid segment"):
        _file("src/not encoded.py")
    with pytest.raises(ValidationError, match="cannot be combined"):
        FileChange(
            current_file_key=file.file_key,
            kinds=(ChangeKind.ADDED, ChangeKind.CONTENT),
        )


def test_unchanged_compatible_snapshot_reuses_every_file() -> None:
    files = (_file("src/a.py"), _file("src/b.py"))
    plan = _plan(files, tuple(reversed(files)))
    assert plan.mode is IncrementalMode.INCREMENTAL
    assert plan.changes == ()
    assert plan.rebuild_file_keys == ()
    assert plan.reuse_file_keys == tuple(sorted(file.file_key for file in files))
