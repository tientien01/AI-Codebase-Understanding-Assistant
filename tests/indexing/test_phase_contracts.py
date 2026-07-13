from __future__ import annotations

import hashlib

from pydantic import ValidationError
import pytest

from app.services.indexing.phase_contracts import (
    IndexPhase,
    PhaseArtifact,
    PhaseInput,
    PhaseResourcePolicy,
)


def _artifact(checksum: str | None = None) -> PhaseArtifact:
    payload = b"snapshot"
    return PhaseArtifact(
        artifact_type="source_snapshot",
        schema_version="source-snapshot/v1",
        key="repositories/repo_one/indexes/idx_one/artifacts/source_snapshot/source.json",
        sha256=checksum or hashlib.sha256(payload).hexdigest(),
        byte_size=len(payload),
        records=1,
    )


def _phase_input(**updates) -> PhaseInput:
    values = {
        "repository_id": "repo_one",
        "index_version_id": "idx_one",
        "phase": IndexPhase.PREFLIGHT,
        "phase_version": "preflight/v1",
        "configuration_sha256": "a" * 64,
        "artifacts": (_artifact(),),
        "resource_policy": PhaseResourcePolicy(
            max_seconds=30,
            max_memory_mb=256,
            max_items=1000,
            max_workers=2,
        ),
    }
    values.update(updates)
    return PhaseInput(**values)


def test_phase_input_idempotency_is_deterministic_and_identity_sensitive() -> None:
    phase_input = _phase_input()
    assert phase_input.idempotency_key() == _phase_input().idempotency_key()
    assert phase_input.idempotency_key() != _phase_input(
        phase_version="preflight/v2"
    ).idempotency_key()
    assert phase_input.idempotency_key() != _phase_input(
        configuration_sha256="b" * 64
    ).idempotency_key()
    assert phase_input.idempotency_key() != _phase_input(
        artifacts=(_artifact("c" * 64),)
    ).idempotency_key()


def test_phase_models_reject_unbounded_policy_foreign_input_and_bad_schema() -> None:
    with pytest.raises(ValidationError):
        PhaseResourcePolicy(
            max_seconds=0,
            max_memory_mb=256,
            max_items=1000,
            max_workers=2,
        )
    foreign = _artifact().model_copy(
        update={
            "key": "repositories/repo_other/indexes/idx_one/artifacts/source_snapshot/source.json"
        }
    )
    with pytest.raises(ValidationError, match="ownership"):
        _phase_input(artifacts=(foreign,))
    with pytest.raises(ValidationError):
        _phase_input(schema_version="phase-input/v2")
    with pytest.raises(ValidationError, match="opaque repository"):
        _phase_input(repository_id="../repo_one")
    with pytest.raises(ValidationError, match="safe logical key"):
        PhaseArtifact(
            **{
                **_artifact().model_dump(),
                "key": "repositories/repo_one/../source.json",
            }
        )
