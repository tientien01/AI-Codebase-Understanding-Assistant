from __future__ import annotations

from datetime import UTC, datetime
import hashlib

from pydantic import ValidationError
import pytest

from app.services.artifacts.manifest import (
    ArtifactManifestPublisher,
    ManifestPublicationError,
)
from app.services.artifacts.models import (
    IndexManifest,
    ManifestArtifact,
    ManifestPipeline,
    ManifestSource,
    ManifestTimestamps,
    ManifestValidation,
)
from app.services.artifacts.store import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    FilesystemArtifactStore,
    manifest_key,
    version_root_key,
)


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _artifact(artifact_type: str, filename: str, payload: bytes) -> ManifestArtifact:
    return ManifestArtifact(
        type=artifact_type,
        schema_version=f"{artifact_type}/v1",
        uri=f"artifacts/{artifact_type}/{filename}",
        sha256=_digest(payload),
        bytes=len(payload),
        records=1,
        required=True,
    )


def _manifest(
    scan: bytes = b'{"files":[]}',
    report: bytes = b'{"status":"passed"}',
) -> IndexManifest:
    scan_artifact = _artifact("scan_result", "scan.json", scan)
    report_artifact = _artifact("validation_report", "report.json", report)
    return IndexManifest(
        schema_version="index-manifest/v1",
        repository_id="repo_one",
        index_version_id="idx_one",
        sequence=1,
        base_index_version_id=None,
        build_kind="full",
        source=ManifestSource(
            type="upload_folder", revision=None, snapshot_sha256="a" * 64
        ),
        pipeline=ManifestPipeline(version="pipeline/v1", configuration_sha256="b" * 64),
        status="ready",
        artifacts=(scan_artifact, report_artifact),
        capabilities={"exploration": {"state": "ready"}},
        coverage={"files": 1},
        validation=ManifestValidation(
            status="passed",
            report_uri=report_artifact.uri,
            report_sha256=report_artifact.sha256,
            critical_issues=0,
        ),
        timestamps=ManifestTimestamps(
            started_at=datetime(2026, 7, 13, 1, tzinfo=UTC),
            finished_at=datetime(2026, 7, 13, 2, tzinfo=UTC),
        ),
    )


def _write_declared_artifacts(
    store: FilesystemArtifactStore,
    manifest: IndexManifest,
    payloads: dict[str, bytes],
) -> None:
    root = version_root_key(manifest.repository_id, manifest.index_version_id)
    for artifact in manifest.artifacts:
        payload = payloads[artifact.type]
        store.write(
            f"{root}/{artifact.uri}",
            [payload],
            expected_sha256=artifact.sha256,
            expected_size=artifact.byte_size,
        )


def test_manifest_round_trip_is_typed_and_deterministic() -> None:
    manifest = _manifest()
    encoded = manifest.canonical_bytes()
    restored = IndexManifest.model_validate_json(encoded)
    assert restored == manifest
    assert restored.canonical_bytes() == encoded
    assert b'"bytes":12' in encoded


def test_manifest_rejects_invalid_schema_identity_uri_and_time() -> None:
    manifest = _manifest()
    payload = manifest.model_dump(mode="python", by_alias=True)
    for field, value in (
        ("schema_version", "index-manifest/v2"),
        ("repository_id", "repository_one"),
    ):
        with pytest.raises(ValidationError):
            IndexManifest.model_validate({**payload, field: value})

    bad_artifact = manifest.artifacts[0].model_copy(
        update={"uri": "../scan.json"}
    )
    with pytest.raises(ValidationError):
        IndexManifest.model_validate(
            {**payload, "artifacts": (bad_artifact, manifest.artifacts[1])}
        )
    naive_times = manifest.timestamps.model_copy(
        update={"finished_at": datetime(2026, 7, 13, 2)}
    )
    with pytest.raises(ValidationError):
        IndexManifest.model_validate({**payload, "timestamps": naive_times})


def test_manifest_publication_verifies_every_object_and_is_idempotent(tmp_path) -> None:
    scan = b'{"files":[]}'
    report = b'{"status":"passed"}'
    manifest = _manifest(scan, report)
    store = FilesystemArtifactStore(tmp_path)
    _write_declared_artifacts(
        store, manifest, {"scan_result": scan, "validation_report": report}
    )

    publisher = ArtifactManifestPublisher(store)
    first = publisher.publish(manifest)
    second = publisher.publish(manifest)
    assert first == second
    assert first.key == manifest_key("repo_one", "idx_one")
    assert store.read_bytes(
        first.key, expected_sha256=first.sha256, expected_size=first.byte_size
    ) == manifest.canonical_bytes()


def test_manifest_publication_rejects_missing_or_corrupt_artifact(tmp_path) -> None:
    scan = b'{"files":[]}'
    report = b'{"status":"passed"}'
    manifest = _manifest(scan, report)
    store = FilesystemArtifactStore(tmp_path)
    root = version_root_key("repo_one", "idx_one")
    report_artifact = manifest.artifacts[1]
    store.write(
        f"{root}/{report_artifact.uri}",
        [report],
        expected_sha256=report_artifact.sha256,
        expected_size=report_artifact.byte_size,
    )
    with pytest.raises(ArtifactNotFoundError):
        ArtifactManifestPublisher(store).publish(manifest)

    scan_artifact = manifest.artifacts[0]
    store.write(
        f"{root}/{scan_artifact.uri}",
        [scan],
        expected_sha256=scan_artifact.sha256,
        expected_size=scan_artifact.byte_size,
    )
    tmp_path.joinpath(*f"{root}/{report_artifact.uri}".split("/")).write_bytes(
        b"corrupt"
    )
    with pytest.raises(ArtifactIntegrityError):
        ArtifactManifestPublisher(store).publish(manifest)


def test_nonterminal_or_undeclared_validation_report_cannot_publish(tmp_path) -> None:
    manifest = _manifest()
    store = FilesystemArtifactStore(tmp_path)
    publisher = ArtifactManifestPublisher(store)
    with pytest.raises(ManifestPublicationError, match="terminal"):
        publisher.publish(manifest.model_copy(update={"status": "building"}))

    without_report = manifest.model_copy(update={"artifacts": (manifest.artifacts[0],)})
    scan = b'{"files":[]}'
    _write_declared_artifacts(store, without_report, {"scan_result": scan})
    with pytest.raises(ManifestPublicationError, match="must be declared"):
        publisher.publish(without_report)
