from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import hashlib

import pytest
from sqlalchemy import func, insert, select, update

from app.db.production_base import ProductionBase
import app.db.production_models  # noqa: F401
from app.services.artifacts.manifest import ArtifactManifestPublisher
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
    FilesystemArtifactStore,
    artifact_key,
)
from app.services.indexing.activation_service import IndexActivationService
from app.services.indexing.job_state_store import (
    ActivationConflictError,
    ActivationValidationError,
    CancellationRequested,
    JobStateStore,
    LeaseLostError,
)
from app.services.indexing.validation_service import (
    CandidateValidationError,
    CandidateValidator,
    CapabilityReadiness,
    ValidationIssue,
)
from tests.jobs.test_job_state_store import _command, _seed


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _manifest(
    repository_id: str = "repo_one",
    index_version_id: str = "idx_one",
    *,
    warning: bool = False,
) -> tuple[IndexManifest, dict[str, bytes]]:
    payloads = {
        "scan_result": b'{"files":[]}',
        "validation_report": b'{"status":"passed"}',
    }
    artifacts = tuple(
        ManifestArtifact(
            type=artifact_type,
            schema_version=f"{artifact_type}/v1",
            uri=f"artifacts/{artifact_type}/{artifact_type}.json",
            sha256=_digest(payload),
            bytes=len(payload),
            records=1,
            required=True,
        )
        for artifact_type, payload in payloads.items()
    )
    report = artifacts[1]
    return (
        IndexManifest(
            schema_version="index-manifest/v1",
            repository_id=repository_id,
            index_version_id=index_version_id,
            sequence=2,
            base_index_version_id=None,
            build_kind="full",
            source=ManifestSource(
                type="upload_folder", revision=None, snapshot_sha256="a" * 64
            ),
            pipeline=ManifestPipeline(
                version="pipeline/v1", configuration_sha256="b" * 64
            ),
            status="ready_with_warnings" if warning else "ready",
            artifacts=artifacts,
            capabilities={
                "exploration": {"state": "limited" if warning else "ready"},
                "semantic": {"state": "failed"},
            },
            coverage={"files": 1},
            validation=ManifestValidation(
                status="passed_with_warnings" if warning else "passed",
                report_uri=report.uri,
                report_sha256=report.sha256,
                critical_issues=0,
            ),
            timestamps=ManifestTimestamps(
                started_at=datetime(2026, 7, 13, 1, tzinfo=UTC),
                finished_at=datetime(2026, 7, 13, 2, tzinfo=UTC),
            ),
        ),
        payloads,
    )


def _readiness(*, exploration_state: str = "ready"):
    return (
        CapabilityReadiness(
            id="capability_exploration",
            capability="exploration",
            state=exploration_state,
            reason_codes=() if exploration_state == "ready" else ("PARTIAL",),
            required_artifact_types=("scan_result",),
            coverage={"files": 1},
        ),
        CapabilityReadiness(
            id="capability_semantic",
            capability="semantic",
            state="failed",
            reason_codes=("PROVIDER_UNAVAILABLE",),
            required_artifact_types=(),
            coverage={},
            remediation="Configure an optional semantic provider.",
        ),
    )


def test_validator_allows_optional_failure_and_safe_mandatory_degradation() -> None:
    manifest, _ = _manifest(warning=True)
    issue = ValidationIssue(
        id="issue_partial",
        code="PARTIAL_COVERAGE",
        severity="warning",
        message_safe="Coverage is partial.",
    )
    candidate = CandidateValidator().validate(
        manifest,
        (issue,),
        _readiness(exploration_state="limited"),
        ("exploration",),
    )
    assert candidate.capabilities[1].state == "failed"
    assert candidate.mandatory_capabilities == ("exploration",)


@pytest.mark.parametrize(
    ("issues", "capabilities", "mandatory", "code"),
    [
        (
            (
                ValidationIssue(
                    id="issue_critical",
                    code="DANGLING_EDGE",
                    severity="critical",
                    message_safe="A critical edge is dangling.",
                ),
            ),
            _readiness(),
            ("exploration",),
            "CRITICAL_VALIDATION_ISSUE",
        ),
        ((), _readiness(exploration_state="failed"), ("exploration",), "MANDATORY_CAPABILITY_NOT_READY"),
        ((), _readiness(), ("graph",), "MANDATORY_CAPABILITY_NOT_READY"),
        (
            (),
            (
                _readiness()[0].model_copy(
                    update={"required_artifact_types": ("graph_result",)}
                ),
                _readiness()[1],
            ),
            ("exploration",),
            "MISSING_REQUIRED_ARTIFACT",
        ),
    ],
)
def test_validator_blocks_critical_or_nonready_mandatory_capability(
    issues, capabilities, mandatory, code
) -> None:
    manifest, _ = _manifest()
    if capabilities[0].state == "failed":
        manifest = manifest.model_copy(
            update={
                "capabilities": {
                    **manifest.capabilities,
                    "exploration": {"state": "failed"},
                }
            }
        )
    with pytest.raises(CandidateValidationError) as caught:
        CandidateValidator().validate(manifest, issues, capabilities, mandatory)
    assert caught.value.code == code


def test_validator_requires_manifest_and_readiness_to_cover_same_capabilities() -> None:
    manifest, _ = _manifest()
    with pytest.raises(CandidateValidationError) as caught:
        CandidateValidator().validate(
            manifest,
            (),
            (_readiness()[0],),
            ("exploration",),
        )
    assert caught.value.code == "CAPABILITY_SUMMARY_MISMATCH"

    optional_scan = manifest.artifacts[0].model_copy(update={"required": False})
    with pytest.raises(CandidateValidationError) as caught:
        CandidateValidator().validate(
            manifest.model_copy(
                update={"artifacts": (optional_scan, manifest.artifacts[1])}
            ),
            (),
            _readiness(),
            ("exploration",),
        )
    assert caught.value.code == "MANDATORY_ARTIFACT_NOT_REQUIRED"


def _activation_fixture(engine, tmp_path, suffix: str):
    ids = _seed(engine, suffix)
    previous_id = f"idx_previous_{suffix}"
    now = datetime(2026, 7, 13, 3, tzinfo=UTC)
    t = ProductionBase.metadata.tables
    with engine.begin() as connection:
        connection.execute(
            insert(t["index_versions"]).values(
                id=previous_id,
                repository_id=ids["repository"],
                version_number=1,
                source_snapshot_id=ids["snapshot"],
                build_kind="full",
                lifecycle="active",
                manifest_schema_version="index-manifest/v1",
                producer_version="test/v1",
                configuration_sha256="a" * 64,
                manifest_storage_key=f"repositories/{ids['repository']}/indexes/{previous_id}/manifest.json",
                manifest_sha256="a" * 64,
                validation_status="passed",
                critical_issue_count=0,
                coverage={},
                finished_at=now,
                activated_at=now,
            )
        )
        connection.execute(
            update(t["repositories"])
            .where(t["repositories"].c.id == ids["repository"])
            .values(active_index_version_id=previous_id)
        )
    state = JobStateStore(engine)
    state.submit(
        replace(
            _command(ids, 2), base_index_version_id=previous_id
        )
    )
    lease = state.claim(
        ids["job"],
        f"worker_{suffix}",
        lease_seconds=60,
        max_attempts=3,
        now=now,
    ).lease
    assert lease is not None

    manifest, payloads = _manifest(ids["repository"], ids["version"])
    manifest = manifest.model_copy(update={"base_index_version_id": previous_id})
    artifact_store = FilesystemArtifactStore(tmp_path)
    for ordinal, artifact in enumerate(manifest.artifacts, start=1):
        key = artifact_key(
            ids["repository"],
            ids["version"],
            artifact.type,
            f"{artifact.type}.json",
        )
        payload = payloads[artifact.type]
        artifact_store.write(
            key,
            [payload],
            expected_sha256=artifact.sha256,
            expected_size=artifact.byte_size,
        )
        state.register_artifact(
            id=f"artifact_{suffix}_{ordinal}",
            repository_id=ids["repository"],
            index_version_id=ids["version"],
            artifact_type=artifact.type,
            storage_key=key,
            schema_version=artifact.schema_version,
            sha256=artifact.sha256,
            byte_size=artifact.byte_size,
            record_count=artifact.records,
            producer_stage="validate",
            producer_name="test",
            producer_version="1",
            required=artifact.required,
            retention_class="active_required",
            finalized_at=now,
        )
    service = IndexActivationService(
        CandidateValidator(), ArtifactManifestPublisher(artifact_store), state
    )
    return t, ids, previous_id, now, lease, manifest, state, service


def test_atomic_activation_switches_every_authoritative_record(production_database, tmp_path) -> None:
    _, engine, _ = production_database
    t, ids, previous, now, lease, manifest, state, service = _activation_fixture(
        engine, tmp_path, "activate"
    )
    result = service.activate(
        lease=lease,
        manifest=manifest,
        issues=(),
        capabilities=_readiness(),
        mandatory_capabilities=("exploration",),
        expected_previous_version_id=previous,
        audit_event_id="audit_activate",
        now=now,
    )
    assert result.active_index_version_id == ids["version"]
    assert result.job_state == "succeeded"
    with engine.connect() as connection:
        assert connection.scalar(
            select(t["repositories"].c.active_index_version_id).where(
                t["repositories"].c.id == ids["repository"]
            )
        ) == ids["version"]
        lifecycles = dict(
            connection.execute(
                select(t["index_versions"].c.id, t["index_versions"].c.lifecycle).where(
                    t["index_versions"].c.id.in_((previous, ids["version"]))
                )
            ).tuples().all()
        )
        assert lifecycles == {previous: "superseded", ids["version"]: "active"}
        assert state.job_state(ids["job"]) == "succeeded"
        assert state.attempt_details(lease.attempt_id)["state"] == "succeeded"
        assert connection.scalar(select(func.count()).select_from(t["audit_events"])) == 1
        assert connection.scalar(select(func.count()).select_from(t["capability_readiness"])) == 2
    repeated = service.activate(
        lease=lease,
        manifest=manifest,
        issues=(),
        capabilities=_readiness(),
        mandatory_capabilities=("exploration",),
        expected_previous_version_id=previous,
        audit_event_id="audit_activate",
        now=now,
    )
    assert repeated.already_active is True
    assert state.request_cancellation(ids["job"], now=now) == "too_late"


def test_activation_rollback_preserves_previous_active_version(production_database, tmp_path) -> None:
    _, engine, _ = production_database
    t, ids, previous, now, lease, manifest, state, service = _activation_fixture(
        engine, tmp_path, "rollback"
    )

    def fail_before_commit() -> None:
        raise RuntimeError("injected transaction failure")

    with pytest.raises(RuntimeError, match="injected"):
        service.activate(
            lease=lease,
            manifest=manifest,
            issues=(),
            capabilities=_readiness(),
            mandatory_capabilities=("exploration",),
            expected_previous_version_id=previous,
            audit_event_id="audit_rollback",
            now=now,
            fault_injector=fail_before_commit,
        )
    with engine.connect() as connection:
        assert connection.scalar(
            select(t["repositories"].c.active_index_version_id).where(
                t["repositories"].c.id == ids["repository"]
            )
        ) == previous
        assert connection.scalar(
            select(t["index_versions"].c.lifecycle).where(
                t["index_versions"].c.id == previous
            )
        ) == "active"
        assert connection.scalar(
            select(t["index_versions"].c.lifecycle).where(
                t["index_versions"].c.id == ids["version"]
            )
        ) == "building"
        assert connection.scalar(select(func.count()).select_from(t["audit_events"])) == 0
        assert connection.scalar(select(func.count()).select_from(t["validation_issues"])) == 0
    assert state.job_state(ids["job"]) == "running"


def test_activation_rejects_cancellation_stale_lease_and_artifact_mismatch(
    production_database, tmp_path
) -> None:
    _, engine, _ = production_database
    t, ids, previous, now, lease, manifest, state, service = _activation_fixture(
        engine, tmp_path, "reject"
    )
    state.request_cancellation(ids["job"], now=now)
    with pytest.raises(CancellationRequested):
        service.activate(
            lease=lease,
            manifest=manifest,
            issues=(),
            capabilities=_readiness(),
            mandatory_capabilities=("exploration",),
            expected_previous_version_id=previous,
            audit_event_id="audit_cancelled",
            now=now,
        )
    with engine.begin() as connection:
        connection.execute(
            update(t["index_jobs"])
            .where(t["index_jobs"].c.id == ids["job"])
            .values(cancellation_requested_at=None)
        )
    with pytest.raises(LeaseLostError):
        service.activate(
            lease=replace(lease, generation=lease.generation + 1),
            manifest=manifest,
            issues=(),
            capabilities=_readiness(),
            mandatory_capabilities=("exploration",),
            expected_previous_version_id=previous,
            audit_event_id="audit_stale",
            now=now,
        )
    with engine.begin() as connection:
        connection.execute(
            update(t["index_artifacts"])
            .where(t["index_artifacts"].c.artifact_type == "scan_result")
            .values(sha256="f" * 64)
        )
    with pytest.raises(ActivationValidationError, match="REGISTERED"):
        service.activate(
            lease=lease,
            manifest=manifest,
            issues=(),
            capabilities=_readiness(),
            mandatory_capabilities=("exploration",),
            expected_previous_version_id=previous,
            audit_event_id="audit_mismatch",
            now=now,
        )
    with engine.connect() as connection:
        assert connection.scalar(
            select(t["repositories"].c.active_index_version_id).where(
                t["repositories"].c.id == ids["repository"]
            )
        ) == previous
        assert connection.scalar(select(func.count()).select_from(t["audit_events"])) == 0


def test_activation_rejects_changed_expected_active_version(production_database, tmp_path) -> None:
    _, engine, _ = production_database
    t, ids, previous, now, lease, manifest, _, service = _activation_fixture(
        engine, tmp_path, "conflict"
    )
    with engine.begin() as connection:
        connection.execute(
            update(t["repositories"])
            .where(t["repositories"].c.id == ids["repository"])
            .values(active_index_version_id=None)
        )
    with pytest.raises(ActivationConflictError, match="EXPECTED_ACTIVE"):
        service.activate(
            lease=lease,
            manifest=manifest,
            issues=(),
            capabilities=_readiness(),
            mandatory_capabilities=("exploration",),
            expected_previous_version_id=previous,
            audit_event_id="audit_conflict",
            now=now,
        )


def test_corrupt_storage_blocks_activation_and_preserves_previous_version(
    production_database, tmp_path
) -> None:
    _, engine, _ = production_database
    t, ids, previous, now, lease, manifest, _, service = _activation_fixture(
        engine, tmp_path, "corrupt"
    )
    scan = manifest.artifacts[0]
    scan_key = artifact_key(
        ids["repository"], ids["version"], scan.type, f"{scan.type}.json"
    )
    tmp_path.joinpath(*scan_key.split("/")).write_bytes(b"corrupt")
    with pytest.raises(ArtifactIntegrityError):
        service.activate(
            lease=lease,
            manifest=manifest,
            issues=(),
            capabilities=_readiness(),
            mandatory_capabilities=("exploration",),
            expected_previous_version_id=previous,
            audit_event_id="audit_corrupt",
            now=now,
        )
    with engine.connect() as connection:
        assert connection.scalar(
            select(t["repositories"].c.active_index_version_id).where(
                t["repositories"].c.id == ids["repository"]
            )
        ) == previous
