from __future__ import annotations

from dataclasses import dataclass
import hashlib

import pytest

from app.services.artifacts.store import (
    ArtifactNotFoundError,
    FilesystemArtifactStore,
    artifact_key,
)
from app.services.indexing.phase_contracts import (
    CANONICAL_PHASE_ORDER,
    CheckpointReference,
    IndexPhase,
    InvalidPhaseRegistryError,
    PhaseArtifact,
    PhaseCancelledError,
    PhaseExecutionContext,
    PhaseExecutionError,
    PhaseFailure,
    PhaseFailureKind,
    PhaseInput,
    PhaseOutput,
    PhaseOutputError,
    PhaseResourcePolicy,
)
from app.services.indexing.phase_pipeline import PhasePipeline, checkpoint_key


OUTPUT_TYPES = (
    "build_plan",
    "scan_result",
    "parse_result",
    "resolve_result",
    "graph_candidates",
    "normalized_graph",
    "validation_result",
    "retrieval_index",
    "optional_views",
    "fingerprints",
)


@dataclass
class SyntheticPhase:
    phase: IndexPhase
    required_input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    store: FilesystemArtifactStore
    version: str = "component/v1"
    resource_policy: PhaseResourcePolicy = PhaseResourcePolicy(
        max_seconds=30,
        max_memory_mb=256,
        max_items=1000,
        max_workers=2,
    )
    executions: int = 0
    fail: bool = False
    failure_kind: PhaseFailureKind | None = None
    cancel_after_output: bool = False
    cancellation_state: dict[str, bool] | None = None
    wrong_output: bool = False

    def execute(
        self, phase_input: PhaseInput, context: PhaseExecutionContext
    ) -> PhaseOutput:
        self.executions += 1
        if self.fail:
            raise RuntimeError("synthetic failure details must not escape")
        if self.failure_kind is not None:
            raise PhaseFailure(self.failure_kind)
        artifact_type = self.output_types[0]
        if self.wrong_output:
            artifact_type = "undeclared_output"
        payload = f"{self.phase.value}:{phase_input.idempotency_key()}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        key = artifact_key(
            phase_input.repository_id,
            phase_input.index_version_id,
            artifact_type,
            f"{self.phase.value}.json",
        )
        self.store.write(
            key,
            [payload],
            expected_sha256=digest,
            expected_size=len(payload),
        )
        if self.cancel_after_output and self.cancellation_state is not None:
            self.cancellation_state["cancelled"] = True
        return PhaseOutput(
            phase=self.phase,
            artifacts=(
                PhaseArtifact(
                    artifact_type=artifact_type,
                    schema_version=f"{artifact_type}/v1",
                    key=key,
                    sha256=digest,
                    byte_size=len(payload),
                    records=1,
                ),
            ),
        )


def _definitions(store: FilesystemArtifactStore) -> tuple[SyntheticPhase, ...]:
    definitions = []
    required = "source_snapshot"
    for phase, output_type in zip(CANONICAL_PHASE_ORDER, OUTPUT_TYPES, strict=True):
        definitions.append(
            SyntheticPhase(phase, (required,), (output_type,), store)
        )
        required = output_type
    return tuple(definitions)


def _source(store: FilesystemArtifactStore) -> PhaseArtifact:
    payload = b"immutable source snapshot"
    digest = hashlib.sha256(payload).hexdigest()
    key = artifact_key(
        "repo_one", "idx_one", "source_snapshot", "source.json"
    )
    store.write(key, [payload], expected_sha256=digest, expected_size=len(payload))
    return PhaseArtifact(
        artifact_type="source_snapshot",
        schema_version="source-snapshot/v1",
        key=key,
        sha256=digest,
        byte_size=len(payload),
        records=1,
    )


def _context(state: dict[str, bool] | None = None) -> PhaseExecutionContext:
    state = state or {"cancelled": False}
    return PhaseExecutionContext(lambda: state["cancelled"])


def _pipeline(store, definitions=None, configuration="a" * 64) -> PhasePipeline:
    return PhasePipeline(
        definitions or _definitions(store),
        store,
        configuration_sha256=configuration,
    )


def test_registry_requires_exact_canonical_order(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    definitions = _definitions(store)
    with pytest.raises(InvalidPhaseRegistryError, match="canonical"):
        _pipeline(store, definitions[:-1])
    with pytest.raises(InvalidPhaseRegistryError, match="canonical"):
        _pipeline(store, (definitions[1], definitions[0], *definitions[2:]))


def test_pipeline_publishes_deterministic_checkpoints_and_retry_resumes(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    source = _source(store)
    first_definitions = _definitions(store)
    first = _pipeline(store, first_definitions).run(
        "repo_one", "idx_one", (source,), (), _context()
    )
    assert len(first.checkpoints) == len(CANONICAL_PHASE_ORDER)
    assert first.checkpoints[0].key == checkpoint_key(
        "repo_one", "idx_one", IndexPhase.PREFLIGHT
    )

    retry_definitions = _definitions(store)
    retry = _pipeline(store, retry_definitions).run(
        "repo_one", "idx_one", (source,), first.checkpoints, _context()
    )
    assert retry.checkpoints == first.checkpoints
    assert all(definition.executions == 0 for definition in retry_definitions)


def test_resume_stops_at_missing_out_of_order_or_incompatible_checkpoint(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    source = _source(store)
    pipeline = _pipeline(store)
    result = pipeline.run("repo_one", "idx_one", (source,), (), _context())

    missing_first = pipeline.plan_resume(
        "repo_one", "idx_one", (source,), result.checkpoints[1:]
    )
    assert missing_first.next_phase_index == 0

    changed_configuration = _pipeline(store, configuration="b" * 64).plan_resume(
        "repo_one", "idx_one", (source,), result.checkpoints
    )
    assert changed_configuration.next_phase_index == 0

    corrupt_reference = result.checkpoints[1].model_copy(
        update={"sha256": "0" * 64}
    )
    corrupt_prefix = pipeline.plan_resume(
        "repo_one",
        "idx_one",
        (source,),
        (result.checkpoints[0], corrupt_reference, *result.checkpoints[2:]),
    )
    assert corrupt_prefix.next_phase_index == 1


def test_corrupt_output_stops_resume_at_owning_phase(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    source = _source(store)
    pipeline = _pipeline(store)
    result = pipeline.run("repo_one", "idx_one", (source,), (), _context())
    first_output = next(
        artifact for artifact in result.artifacts if artifact.artifact_type == "build_plan"
    )
    tmp_path.joinpath(*first_output.key.split("/")).write_bytes(b"corrupt")

    plan = pipeline.plan_resume(
        "repo_one", "idx_one", (source,), result.checkpoints
    )
    assert plan.next_phase_index == 0


def test_failure_and_cancellation_never_publish_completed_checkpoint(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    source = _source(store)
    failing = list(_definitions(store))
    failing[0].fail = True
    with pytest.raises(PhaseExecutionError, match="preflight") as caught:
        _pipeline(store, tuple(failing)).run(
            "repo_one", "idx_one", (source,), (), _context()
        )
    assert "synthetic failure" not in str(caught.value)
    with pytest.raises(ArtifactNotFoundError):
        store.verify(
            checkpoint_key("repo_one", "idx_one", IndexPhase.PREFLIGHT),
            expected_sha256="0" * 64,
            expected_size=0,
        )

    state = {"cancelled": False}
    cancelling = list(_definitions(store))
    cancelling[0].cancel_after_output = True
    cancelling[0].cancellation_state = state
    with pytest.raises(PhaseCancelledError):
        _pipeline(store, tuple(cancelling)).run(
            "repo_one", "idx_one", (source,), (), _context(state)
        )
    with pytest.raises(ArtifactNotFoundError):
        store.verify(
            checkpoint_key("repo_one", "idx_one", IndexPhase.PREFLIGHT),
            expected_sha256="0" * 64,
            expected_size=0,
        )


def test_undeclared_output_is_rejected_before_checkpoint_publication(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    definitions = list(_definitions(store))
    definitions[0].wrong_output = True
    with pytest.raises(PhaseOutputError, match="undeclared"):
        _pipeline(store, tuple(definitions)).run(
            "repo_one", "idx_one", (_source(store),), (), _context()
        )


def test_phase_failure_classification_is_preserved_without_details(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    definitions = list(_definitions(store))
    definitions[0].failure_kind = PhaseFailureKind.TRANSIENT
    with pytest.raises(PhaseExecutionError) as caught:
        _pipeline(store, tuple(definitions)).run(
            "repo_one", "idx_one", (_source(store),), (), _context()
        )
    assert caught.value.kind is PhaseFailureKind.TRANSIENT
    assert caught.value.retryable is True
    assert "synthetic" not in str(caught.value)
