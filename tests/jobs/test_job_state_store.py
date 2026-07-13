from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import insert, select

from app.db.production_base import ProductionBase
import app.db.production_models  # noqa: F401
from app.services.indexing.job_state_store import JobStateStore, JobSubmission, StateTransitionError


DIGEST = "a" * 64


def _seed(engine, suffix: str = "one"):
    t = ProductionBase.metadata.tables
    ids = {
        "principal": f"principal_{suffix}", "repository": f"repo_{suffix}",
        "source": f"source_{suffix}", "snapshot": f"snapshot_{suffix}",
        "idem": f"idem_{suffix}", "job": f"job_{suffix}", "version": f"idx_{suffix}",
    }
    with engine.begin() as connection:
        connection.execute(insert(t["operator_principals"]).values(id=ids["principal"], display_name="Test"))
        connection.execute(insert(t["repositories"]).values(id=ids["repository"], owner_principal_id=ids["principal"], display_name="Test"))
        connection.execute(insert(t["repository_sources"]).values(id=ids["source"], repository_id=ids["repository"], source_type="upload_folder"))
        connection.execute(insert(t["source_snapshots"]).values(id=ids["snapshot"], repository_id=ids["repository"], repository_source_id=ids["source"], storage_key=f"repositories/{ids['repository']}/source", snapshot_sha256=DIGEST, policy_version="1", inventory_schema_version="1", total_files=0, total_bytes=0))
    return ids


def _command(ids, number: int = 1):
    return JobSubmission(job_id=ids["job"], repository_id=ids["repository"], source_snapshot_id=ids["snapshot"], version_id=ids["version"], version_number=number, principal_id=ids["principal"], idempotency_record_id=ids["idem"], idempotency_key=ids["job"], request_sha256=DIGEST)


def test_submission_and_declared_transitions(production_database) -> None:
    _, engine, _ = production_database
    ids = _seed(engine)
    store = JobStateStore(engine)
    store.submit(_command(ids))
    assert store.job_state(ids["job"]) == "queued"
    store.transition_job(ids["job"], "queued", "running")
    store.transition_version(ids["version"], "building", "validating")
    store.transition_job(ids["job"], "running", "failed")
    store.transition_version(ids["version"], "validating", "failed")
    assert store.job_state(ids["job"]) == "failed"


def test_stale_and_invalid_transitions_are_rejected(production_database) -> None:
    _, engine, _ = production_database
    ids = _seed(engine)
    store = JobStateStore(engine)
    store.submit(_command(ids))
    with pytest.raises(StateTransitionError, match="Invalid"):
        store.transition_job(ids["job"], "queued", "succeeded")
    store.transition_job(ids["job"], "queued", "running")
    with pytest.raises(StateTransitionError, match="changed before"):
        store.transition_job(ids["job"], "queued", "cancelled")


def test_second_active_job_conflict_rolls_back_submission(production_database) -> None:
    _, engine, _ = production_database
    first = _seed(engine)
    store = JobStateStore(engine)
    store.submit(_command(first))
    second = {**first, "job": "job_two", "version": "idx_two", "idem": "idem_two"}
    with pytest.raises(StateTransitionError, match="conflicts"):
        store.submit(_command(second, 2))
    t = ProductionBase.metadata.tables
    with engine.connect() as connection:
        assert connection.scalar(select(t["index_versions"].c.id).where(t["index_versions"].c.id == "idx_two")) is None


def test_artifact_is_immutable_and_repository_bound(production_database) -> None:
    _, engine, _ = production_database
    ids = _seed(engine)
    store = JobStateStore(engine)
    store.submit(_command(ids))
    artifact = dict(id="artifact_one", repository_id=ids["repository"], index_version_id=ids["version"], artifact_type="scan", storage_key="repositories/repo_one/indexes/idx_one/scan.json", schema_version="scan/v1", sha256=DIGEST, byte_size=10, record_count=1, producer_stage="scan", producer_name="test", producer_version="1", required=True, retention_class="active_required", finalized_at=datetime.now(UTC))
    store.register_artifact(**artifact)
    with pytest.raises(StateTransitionError, match="conflicts"):
        store.register_artifact(**{**artifact, "byte_size": 11})
