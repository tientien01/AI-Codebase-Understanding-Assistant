"""Verification and immutable publication of terminal index manifests."""

from __future__ import annotations

import hashlib

from app.services.artifacts.models import IndexManifest
from app.services.artifacts.store import (
    ArtifactStorePort,
    StoredArtifact,
    manifest_key,
    version_root_key,
)


class ManifestPublicationError(RuntimeError):
    pass


class ArtifactManifestPublisher:
    TERMINAL_STATUSES = {"ready", "ready_with_warnings", "failed", "cancelled"}

    def __init__(self, store: ArtifactStorePort) -> None:
        self.store = store

    def publish(self, manifest: IndexManifest) -> StoredArtifact:
        if manifest.status not in self.TERMINAL_STATUSES:
            raise ManifestPublicationError("Only a terminal manifest can be published")
        root = version_root_key(manifest.repository_id, manifest.index_version_id)
        for artifact in manifest.artifacts:
            self.store.verify(
                f"{root}/{artifact.uri}",
                expected_sha256=artifact.sha256,
                expected_size=artifact.byte_size,
            )
        report_size = self.store.verify(
            f"{root}/{manifest.validation.report_uri}",
            expected_sha256=manifest.validation.report_sha256,
            expected_size=self._report_size(root, manifest),
        ).byte_size
        if report_size < 0:  # Defensive contract guard for alternate adapters.
            raise ManifestPublicationError("Validation report size is invalid")

        payload = manifest.canonical_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        return self.store.write(
            manifest_key(manifest.repository_id, manifest.index_version_id),
            [payload],
            expected_sha256=digest,
            expected_size=len(payload),
        )

    def _report_size(self, root: str, manifest: IndexManifest) -> int:
        """Resolve report size from its declared artifact entry."""
        report_key = f"{root}/{manifest.validation.report_uri}"
        for artifact in manifest.artifacts:
            if f"{root}/{artifact.uri}" == report_key:
                return artifact.byte_size
        raise ManifestPublicationError(
            "Validation report must be declared as a manifest artifact"
        )
