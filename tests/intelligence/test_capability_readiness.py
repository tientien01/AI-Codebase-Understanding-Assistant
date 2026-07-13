from __future__ import annotations

import pytest

from app.services.code_analysis.capability_readiness import (
    ArtifactEvidence,
    CapabilityEvidence,
    CapabilityReadinessCalculator,
    CapabilitySpec,
)


def spec(
    capability: str,
    *,
    mandatory: bool = False,
    artifacts: tuple[str, ...] = ("parsed_file",),
    dependencies: tuple[str, ...] = (),
    provider: bool = False,
) -> CapabilitySpec:
    return CapabilitySpec(
        capability=capability,
        mandatory=mandatory,
        required_artifact_types=artifacts,
        dependencies=dependencies,
        requires_provider=provider,
    )


def evidence(
    capability: str,
    *,
    artifact_type: str = "parsed_file",
    artifact_state: str = "ready",
    total: int = 10,
    successful: int = 10,
    unresolved: int = 0,
    issues: tuple[str, ...] = (),
    freshness: str = "fresh",
    supported: bool = True,
    provider: bool = True,
) -> CapabilityEvidence:
    return CapabilityEvidence(
        capability=capability,
        artifacts=(ArtifactEvidence(artifact_type=artifact_type, state=artifact_state),),
        total_units=total,
        successful_units=successful,
        unresolved_references=unresolved,
        critical_issue_ids=issues,
        source_freshness=freshness,
        supported=supported,
        provider_available=provider,
    )


def calculate(specs: tuple[CapabilitySpec, ...], items: tuple[CapabilityEvidence, ...]):
    return CapabilityReadinessCalculator().calculate(
        repository_id="repo_readiness",
        index_version_id="idx_readiness_v1",
        specs=specs,
        evidence=items,
    )


def by_name(report):
    return {item.capability: item for item in report.readiness}


def test_readiness_matrix_covers_all_contract_states() -> None:
    specs = (
        spec("exploration", mandatory=True, artifacts=("scan_result",)),
        spec("symbols", mandatory=True),
        spec("graph", dependencies=("symbols",), artifacts=("normalized_graph",)),
        spec("semantic", provider=True, artifacts=("semantic_index",)),
        spec("failed_profile"),
        spec("stale_source"),
    )
    items = (
        evidence("exploration", artifact_type="scan_result"),
        evidence("symbols", successful=9),
        evidence("graph", artifact_type="normalized_graph", total=20, successful=20, unresolved=3),
        evidence("semantic", artifact_type="semantic_index", provider=False),
        evidence("failed_profile", successful=0),
        evidence("stale_source", freshness="stale"),
    )

    report = calculate(specs, items)
    states = {name: item.state for name, item in by_name(report).items()}

    assert states == {
        "exploration": "ready",
        "failed_profile": "failed",
        "graph": "limited",
        "semantic": "unavailable",
        "stale_source": "stale",
        "symbols": "limited",
    }
    assert report.activation_allowed
    assert by_name(report)["symbols"].coverage["success_fraction"] == 0.9
    assert by_name(report)["graph"].reason_codes == ("DEPENDENCY_LIMITED", "UNRESOLVED_REFERENCES_PRESENT")


def test_partial_and_unresolved_mandatory_capabilities_remain_activatable() -> None:
    report = calculate(
        (spec("symbols", mandatory=True), spec("references", mandatory=True, dependencies=("symbols",))),
        (evidence("symbols", successful=8), evidence("references", total=5, successful=5, unresolved=2)),
    )

    assert report.activation_allowed
    assert by_name(report)["symbols"].state == "limited"
    assert by_name(report)["references"].state == "limited"


@pytest.mark.parametrize(
    ("artifact_state", "expected_state", "reason"),
    [
        ("missing", "unavailable", "REQUIRED_ARTIFACT_MISSING"),
        ("failed", "failed", "REQUIRED_ARTIFACT_FAILED"),
        ("stale", "stale", "SOURCE_OR_ARTIFACT_STALE"),
    ],
)
def test_required_artifact_failures_are_capability_scoped(artifact_state: str, expected_state: str, reason: str) -> None:
    report = calculate(
        (spec("core", mandatory=True), spec("optional")),
        (evidence("core"), evidence("optional", artifact_state=artifact_state)),
    )

    assert by_name(report)["core"].state == "ready"
    assert by_name(report)["optional"].state == expected_state
    assert by_name(report)["optional"].reason_codes == (reason,)
    assert report.activation_allowed


def test_critical_mandatory_capability_blocks_activation_and_links_issue() -> None:
    report = calculate(
        (spec("graph", mandatory=True, artifacts=("normalized_graph",)),),
        (evidence("graph", artifact_type="normalized_graph", issues=("issue_dangling",)),),
    )
    readiness = report.readiness[0]

    assert readiness.state == "failed"
    assert readiness.validation_issue_id == "issue_dangling"
    assert readiness.reason_codes == ("CRITICAL_VALIDATION_ISSUE",)
    assert not report.activation_allowed


def test_dependency_failure_is_propagated_without_changing_unrelated_capability() -> None:
    report = calculate(
        (spec("symbols"), spec("graph", dependencies=("symbols",)), spec("exploration", mandatory=True)),
        (evidence("symbols", successful=0), evidence("graph"), evidence("exploration")),
    )

    assert by_name(report)["symbols"].state == "failed"
    assert by_name(report)["graph"].state == "unavailable"
    assert by_name(report)["graph"].reason_codes == ("DEPENDENCY_FAILED",)
    assert by_name(report)["exploration"].state == "ready"
    assert report.activation_allowed


def test_reordered_inputs_produce_byte_equivalent_report() -> None:
    specs = (spec("core", mandatory=True, artifacts=("scan_result",)), spec("graph", dependencies=("core",)))
    items = (
        CapabilityEvidence(
            capability="core",
            artifacts=(ArtifactEvidence(artifact_type="scan_result", state="ready"),),
            total_units=2,
            successful_units=2,
        ),
        evidence("graph", successful=1, total=2),
    )

    assert calculate(specs, items).to_json() == calculate(tuple(reversed(specs)), tuple(reversed(items))).to_json()


@pytest.mark.parametrize("case", ["cycle", "unknown", "set_mismatch"])
def test_invalid_dependency_or_evidence_contract_fails_closed(case: str) -> None:
    if case == "cycle":
        specs = (spec("a", dependencies=("b",)), spec("b", dependencies=("a",)))
        items = (evidence("a"), evidence("b"))
    elif case == "unknown":
        specs = (spec("a", dependencies=("missing",)),)
        items = (evidence("a"),)
    else:
        specs = (spec("a"),)
        items = (evidence("b"),)

    with pytest.raises(ValueError):
        calculate(specs, items)
