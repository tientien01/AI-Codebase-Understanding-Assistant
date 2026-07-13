"""Internal validation, immutable publication, and atomic activation boundary."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from app.services.artifacts.manifest import ArtifactManifestPublisher
from app.services.artifacts.models import IndexManifest
from app.services.indexing.job_state_store import (
    ActivationCommand,
    ActivationResult,
    JobLease,
    JobStateStore,
)
from app.services.indexing.validation_service import (
    CandidateValidator,
    CapabilityReadiness,
    ValidationIssue,
)


class IndexActivationService:
    def __init__(
        self,
        validator: CandidateValidator,
        publisher: ArtifactManifestPublisher,
        state_store: JobStateStore,
    ) -> None:
        self.validator = validator
        self.publisher = publisher
        self.state_store = state_store

    def activate(
        self,
        *,
        lease: JobLease,
        manifest: IndexManifest,
        issues: tuple[ValidationIssue, ...],
        capabilities: tuple[CapabilityReadiness, ...],
        mandatory_capabilities: tuple[str, ...],
        expected_previous_version_id: str | None,
        audit_event_id: str,
        now: datetime | None = None,
        fault_injector: Callable[[], None] | None = None,
    ) -> ActivationResult:
        candidate = self.validator.validate(
            manifest, issues, capabilities, mandatory_capabilities
        )
        stored_manifest = self.publisher.publish(manifest)
        return self.state_store.activate(
            ActivationCommand(
                lease=lease,
                candidate=candidate,
                manifest_artifact=stored_manifest,
                expected_previous_version_id=expected_previous_version_id,
                audit_event_id=audit_event_id,
            ),
            now=now,
            fault_injector=fault_injector,
        )
