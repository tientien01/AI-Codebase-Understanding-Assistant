from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib

import pytest

from app.services.artifacts.store import (
    ArtifactConflictError,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    FilesystemArtifactStore,
    UnsafeArtifactKeyError,
    artifact_key,
    validate_logical_key,
)


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize(
    "key",
    [
        "",
        "/absolute/object.json",
        "repositories\\repo_one\\object.json",
        "repositories/repo_one/../escape.json",
        "repositories//object.json",
        "repositories/CON/object.json",
        "repositories/repo_one/object.",
        "repositories/repo_one/bad:key.json",
    ],
)
def test_logical_key_rejects_nonportable_or_escaping_paths(key: str) -> None:
    with pytest.raises(UnsafeArtifactKeyError):
        validate_logical_key(key)


def test_artifact_key_enforces_repository_and_version_ownership() -> None:
    assert artifact_key(
        "repo_one", "idx_one", "scan_result", "scan-result.json"
    ) == (
        "repositories/repo_one/indexes/idx_one/"
        "artifacts/scan_result/scan-result.json"
    )
    with pytest.raises(UnsafeArtifactKeyError, match="repository"):
        artifact_key("other", "idx_one", "scan_result", "scan.json")
    with pytest.raises(UnsafeArtifactKeyError, match="reserved"):
        artifact_key(
            "repo_one", "idx_one", "scan_result", "manifest.json"
        )


def test_exact_write_is_verified_idempotent_and_immutable(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    key = artifact_key("repo_one", "idx_one", "scan_result", "scan.json")
    payload = b'{"files":[]}'
    digest = _digest(payload)

    first = store.write(
        key, [payload[:5], payload[5:]], expected_sha256=digest, expected_size=len(payload)
    )
    second = store.write(
        key, [payload], expected_sha256=digest, expected_size=len(payload)
    )
    assert first == second
    assert store.read_bytes(
        key, expected_sha256=digest, expected_size=len(payload)
    ) == payload

    conflicting = b"different"
    with pytest.raises(ArtifactConflictError, match="different bytes"):
        store.write(
            key,
            [conflicting],
            expected_sha256=_digest(conflicting),
            expected_size=len(conflicting),
        )
    assert store.read_bytes(
        key, expected_sha256=digest, expected_size=len(payload)
    ) == payload


def test_declared_metadata_mismatch_leaves_no_object_or_temporary_file(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    key = artifact_key("repo_one", "idx_one", "scan_result", "scan.json")
    payload = b"payload"
    with pytest.raises(ArtifactIntegrityError, match="declared metadata"):
        store.write(
            key,
            [payload],
            expected_sha256="0" * 64,
            expected_size=len(payload),
        )
    assert not list(tmp_path.rglob(".artifact-*"))
    with pytest.raises(ArtifactNotFoundError):
        store.verify(key, expected_sha256=_digest(payload), expected_size=len(payload))


def test_verified_read_rejects_corruption_without_exposing_root(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    key = artifact_key("repo_one", "idx_one", "scan_result", "scan.json")
    payload = b"trusted"
    digest = _digest(payload)
    store.write(key, [payload], expected_sha256=digest, expected_size=len(payload))
    tmp_path.joinpath(*key.split("/")).write_bytes(b"corrupt")

    with pytest.raises(ArtifactIntegrityError) as caught:
        store.read_bytes(key, expected_sha256=digest, expected_size=len(payload))
    assert str(tmp_path) not in str(caught.value)


def test_concurrent_identical_finalize_has_one_authoritative_object(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    key = artifact_key("repo_one", "idx_one", "scan_result", "scan.json")
    payload = b"concurrent immutable payload"
    digest = _digest(payload)

    def write_once(_index: int):
        return store.write(
            key, [payload], expected_sha256=digest, expected_size=len(payload)
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(write_once, range(8)))
    assert len(set(results)) == 1
    assert store.read_bytes(
        key, expected_sha256=digest, expected_size=len(payload)
    ) == payload
