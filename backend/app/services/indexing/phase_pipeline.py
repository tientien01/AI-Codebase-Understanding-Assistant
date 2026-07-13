"""Storage-backed execution and validated-prefix resume for indexing phases."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from pydantic import ValidationError

from app.services.artifacts.store import (
    ArtifactStoreError,
    ArtifactStorePort,
    artifact_key,
)
from app.services.indexing.phase_contracts import (
    CANONICAL_PHASE_ORDER,
    CheckpointReference,
    IndexPhase,
    IndexPhaseDefinition,
    InvalidPhaseRegistryError,
    PhaseArtifact,
    PhaseCancelledError,
    PhaseCheckpoint,
    PhaseExecutionContext,
    PhaseExecutionError,
    PhaseFailure,
    PhaseFailureKind,
    PhaseInput,
    PhaseInputError,
    PhaseOutput,
    PhaseOutputError,
)


STABLE_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def checkpoint_key(
    repository_id: str, index_version_id: str, phase: IndexPhase
) -> str:
    ordinal = CANONICAL_PHASE_ORDER.index(phase) + 1
    return artifact_key(
        repository_id,
        index_version_id,
        "phase_checkpoint",
        f"{ordinal:02d}-{phase.value}.json",
    )


@dataclass(frozen=True)
class ResumePlan:
    next_phase_index: int
    completed: tuple[CheckpointReference, ...]
    artifacts: tuple[PhaseArtifact, ...]


@dataclass(frozen=True)
class PipelineRunResult:
    checkpoints: tuple[CheckpointReference, ...]
    artifacts: tuple[PhaseArtifact, ...]


class PhasePipeline:
    def __init__(
        self,
        definitions: tuple[IndexPhaseDefinition, ...],
        store: ArtifactStorePort,
        *,
        configuration_sha256: str,
    ) -> None:
        self.definitions = definitions
        self.store = store
        self.configuration_sha256 = configuration_sha256
        self._validate_registry()
        if not re.fullmatch(r"[0-9a-f]{64}", configuration_sha256):
            raise InvalidPhaseRegistryError(
                "Pipeline configuration identity must be lowercase SHA-256"
            )

    def plan_resume(
        self,
        repository_id: str,
        index_version_id: str,
        initial_artifacts: tuple[PhaseArtifact, ...],
        checkpoint_references: tuple[CheckpointReference, ...],
    ) -> ResumePlan:
        pool = self._artifact_pool(
            initial_artifacts, repository_id, index_version_id
        )
        completed: list[CheckpointReference] = []
        for index, definition in enumerate(self.definitions):
            if index >= len(checkpoint_references):
                break
            reference = checkpoint_references[index]
            if (
                reference.phase != definition.phase
                or reference.key
                != checkpoint_key(repository_id, index_version_id, definition.phase)
            ):
                break
            phase_input = self._build_input(
                definition, repository_id, index_version_id, pool
            )
            checkpoint = self._load_compatible_checkpoint(
                reference, definition, phase_input
            )
            if checkpoint is None:
                break
            try:
                self._verify_output(checkpoint.output.artifacts)
            except (ArtifactStoreError, PhaseOutputError):
                break
            self._merge_outputs(pool, checkpoint.output.artifacts)
            completed.append(reference)
        return ResumePlan(
            next_phase_index=len(completed),
            completed=tuple(completed),
            artifacts=tuple(pool.values()),
        )

    def run(
        self,
        repository_id: str,
        index_version_id: str,
        initial_artifacts: tuple[PhaseArtifact, ...],
        checkpoint_references: tuple[CheckpointReference, ...],
        context: PhaseExecutionContext,
    ) -> PipelineRunResult:
        plan = self.plan_resume(
            repository_id,
            index_version_id,
            initial_artifacts,
            checkpoint_references,
        )
        pool = self._artifact_pool(
            plan.artifacts, repository_id, index_version_id
        )
        completed = list(plan.completed)
        for definition in self.definitions[plan.next_phase_index :]:
            context.check_cancelled()
            phase_input = self._build_input(
                definition, repository_id, index_version_id, pool
            )
            context.progress(definition.phase, 0)
            try:
                output = definition.execute(phase_input, context)
            except PhaseCancelledError:
                raise
            except PhaseFailure as failure:
                raise PhaseExecutionError(
                    definition.phase, failure.kind
                ) from None
            except Exception:
                raise PhaseExecutionError(
                    definition.phase, PhaseFailureKind.PERMANENT
                ) from None
            self._validate_output(
                definition, output, repository_id, index_version_id
            )
            self._verify_output(output.artifacts)
            context.check_cancelled()
            checkpoint = PhaseCheckpoint(
                repository_id=repository_id,
                index_version_id=index_version_id,
                phase=definition.phase,
                phase_version=definition.version,
                idempotency_key=phase_input.idempotency_key(),
                configuration_sha256=self.configuration_sha256,
                output=output,
            )
            payload = checkpoint.canonical_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            stored = self.store.write(
                checkpoint_key(repository_id, index_version_id, definition.phase),
                [payload],
                expected_sha256=digest,
                expected_size=len(payload),
            )
            reference = CheckpointReference(
                phase=definition.phase,
                key=stored.key,
                sha256=stored.sha256,
                byte_size=stored.byte_size,
            )
            completed.append(reference)
            self._merge_outputs(pool, output.artifacts)
            context.progress(definition.phase, 100)
        return PipelineRunResult(tuple(completed), tuple(pool.values()))

    def _validate_registry(self) -> None:
        phases = tuple(definition.phase for definition in self.definitions)
        if phases != CANONICAL_PHASE_ORDER:
            raise InvalidPhaseRegistryError(
                "Index phase registry must match the canonical production-v1 order"
            )
        for definition in self.definitions:
            if not definition.version or len(definition.version) > 128:
                raise InvalidPhaseRegistryError(
                    f"Index phase {definition.phase.value} has an invalid version"
                )
            for artifact_type in (
                *definition.required_input_types,
                *definition.output_types,
            ):
                if not STABLE_NAME.fullmatch(artifact_type):
                    raise InvalidPhaseRegistryError(
                        f"Index phase {definition.phase.value} has an invalid artifact type"
                    )
            if len(definition.required_input_types) != len(
                set(definition.required_input_types)
            ) or len(definition.output_types) != len(set(definition.output_types)):
                raise InvalidPhaseRegistryError(
                    f"Index phase {definition.phase.value} repeats an artifact type"
                )

    def _build_input(
        self,
        definition: IndexPhaseDefinition,
        repository_id: str,
        index_version_id: str,
        pool: dict[str, PhaseArtifact],
    ) -> PhaseInput:
        missing = [
            artifact_type
            for artifact_type in definition.required_input_types
            if artifact_type not in pool
        ]
        if missing:
            raise PhaseInputError(
                f"Index phase {definition.phase.value} is missing declared input"
            )
        return PhaseInput(
            repository_id=repository_id,
            index_version_id=index_version_id,
            phase=definition.phase,
            phase_version=definition.version,
            configuration_sha256=self.configuration_sha256,
            artifacts=tuple(pool[kind] for kind in definition.required_input_types),
            resource_policy=definition.resource_policy,
        )

    def _load_compatible_checkpoint(
        self,
        reference: CheckpointReference,
        definition: IndexPhaseDefinition,
        phase_input: PhaseInput,
    ) -> PhaseCheckpoint | None:
        try:
            payload = self.store.read_bytes(
                reference.key,
                expected_sha256=reference.sha256,
                expected_size=reference.byte_size,
            )
            checkpoint = PhaseCheckpoint.model_validate_json(payload)
        except (ArtifactStoreError, ValidationError, ValueError):
            return None
        if (
            checkpoint.repository_id != phase_input.repository_id
            or checkpoint.index_version_id != phase_input.index_version_id
            or checkpoint.phase != definition.phase
            or checkpoint.phase_version != definition.version
            or checkpoint.configuration_sha256 != self.configuration_sha256
            or checkpoint.idempotency_key != phase_input.idempotency_key()
            or checkpoint.output.phase != definition.phase
            or tuple(a.artifact_type for a in checkpoint.output.artifacts)
            != definition.output_types
        ):
            return None
        return checkpoint

    def _validate_output(
        self,
        definition: IndexPhaseDefinition,
        output: PhaseOutput,
        repository_id: str,
        index_version_id: str,
    ) -> None:
        if output.phase != definition.phase:
            raise PhaseOutputError(
                f"Index phase {definition.phase.value} returned another phase"
            )
        if tuple(a.artifact_type for a in output.artifacts) != definition.output_types:
            raise PhaseOutputError(
                f"Index phase {definition.phase.value} returned undeclared output"
            )
        owner_prefix = (
            f"repositories/{repository_id}/indexes/{index_version_id}/"
        )
        if any(not artifact.key.startswith(owner_prefix) for artifact in output.artifacts):
            raise PhaseOutputError(
                f"Index phase {definition.phase.value} returned foreign output"
            )

    def _verify_output(self, artifacts: tuple[PhaseArtifact, ...]) -> None:
        for artifact in artifacts:
            self.store.verify(
                artifact.key,
                expected_sha256=artifact.sha256,
                expected_size=artifact.byte_size,
            )

    def _artifact_pool(
        self,
        artifacts: tuple[PhaseArtifact, ...],
        repository_id: str,
        index_version_id: str,
    ) -> dict[str, PhaseArtifact]:
        pool: dict[str, PhaseArtifact] = {}
        owner_prefix = (
            f"repositories/{repository_id}/indexes/{index_version_id}/"
        )
        for artifact in artifacts:
            if not artifact.key.startswith(owner_prefix):
                raise PhaseInputError("Initial artifact has incompatible ownership")
            if artifact.artifact_type in pool:
                raise PhaseInputError("Initial artifact types must be unique")
            pool[artifact.artifact_type] = artifact
        return pool

    def _merge_outputs(
        self,
        pool: dict[str, PhaseArtifact],
        artifacts: tuple[PhaseArtifact, ...],
    ) -> None:
        for artifact in artifacts:
            pool[artifact.artifact_type] = artifact
