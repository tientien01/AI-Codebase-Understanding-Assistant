from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.services.evaluation.dataset import load_dataset
from app.services.evaluation.gates import evaluate_gate, load_gate_configuration, main
from app.services.evaluation.runner import run_evaluation


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "evaluation" / "datasets" / "retrieval-v1"
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "retrieval_benchmark_repo"
GATE_PATH = PROJECT_ROOT / "evaluation" / "gates" / "eva-002-ci.json"


def _run() -> dict:
    dataset = load_dataset(DATASET_ROOT, FIXTURE_ROOT)
    return run_evaluation(
        dataset,
        code_revision="EVA-002-ci-smoke",
        index_version_id="idx_eva_002_ci",
        started_at="2026-07-14T00:00:00Z",
        completed_at="2026-07-14T00:00:00Z",
    )


def _diagnostics(result: dict) -> dict[str, dict]:
    return {item["rule_id"]: item for item in result["diagnostics"]}


def test_checked_in_gate_is_content_addressed_non_release_and_passes_frozen_run() -> None:
    configuration = load_gate_configuration(GATE_PATH)

    result = evaluate_gate(configuration, _run())

    assert configuration.classification == "ci_regression_only"
    assert configuration.config_id.startswith("evalgate_")
    assert result["passed"] is True
    assert result["gate_config_id"] == configuration.config_id
    assert result["semantic_checksum"].startswith("sha256:")
    assert all(item["passed"] for item in result["diagnostics"])


def test_gate_identity_and_diagnostics_are_invariant_to_rule_declaration_order() -> None:
    configuration = load_gate_configuration(GATE_PATH)
    reordered = replace(configuration, rules=tuple(reversed(configuration.rules)))

    assert reordered.config_id == configuration.config_id
    assert evaluate_gate(reordered, _run()) == evaluate_gate(configuration, _run())


@pytest.mark.parametrize(
    ("mutate", "failed_rule", "reason"),
    [
        (
            lambda run: run.update(dataset_revision="sha256:" + "0" * 64),
            "identity:dataset_revision",
            "identity_mismatch",
        ),
        (
            lambda run: run["methods"][0]["cases"][0].update(status="failed", error_code="fixture_failure"),
            "method:exact_keyword:cases_completed",
            "missing_or_errored_cases",
        ),
        (
            lambda run: run["methods"][2]["aggregates"]["3"].update(recall_at_k=0.5),
            "hybrid-recall-at-3",
            "metric_regression",
        ),
        (
            lambda run: run["methods"][2]["aggregates"]["3"].update(ndcg_at_k=float("nan")),
            "hybrid-ndcg-at-3",
            "metric_non_finite",
        ),
    ],
)
def test_identity_case_and_metric_regressions_fail_closed(mutate, failed_rule: str, reason: str) -> None:
    configuration = load_gate_configuration(GATE_PATH)
    run = deepcopy(_run())
    mutate(run)

    result = evaluate_gate(configuration, run)

    assert result["passed"] is False
    assert _diagnostics(result)[failed_rule]["reason_code"] == reason


def test_missing_method_or_metric_is_a_failed_decision() -> None:
    configuration = load_gate_configuration(GATE_PATH)
    run = deepcopy(_run())
    run["methods"] = [item for item in run["methods"] if item["method"] != "naive_semantic"]

    result = evaluate_gate(configuration, run)

    diagnostics = _diagnostics(result)
    assert result["passed"] is False
    assert diagnostics["identity:method_config:naive_semantic"]["passed"] is False
    assert diagnostics["naive-semantic-recall-at-3"]["reason_code"] == "metric_missing_or_undefined"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda config: config.update(classification="release_threshold"),
        lambda config: config["rules"].append(dict(config["rules"][0])),
        lambda config: config["rules"][0].update(metric="unknown"),
        lambda config: config["rules"][0].update(bound=float("inf")),
    ],
)
def test_invalid_gate_configuration_is_rejected(tmp_path: Path, mutate) -> None:
    raw = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    mutate(raw)
    path = tmp_path / "gate.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError):
        load_gate_configuration(path)


def test_cli_writes_pass_and_returns_nonzero_for_regression(tmp_path: Path) -> None:
    run_path = tmp_path / "run.json"
    pass_output = tmp_path / "pass.json"
    fail_output = tmp_path / "fail.json"
    run = _run()
    run_path.write_text(json.dumps(run), encoding="utf-8")

    assert main(["--config", str(GATE_PATH), "--run", str(run_path), "--output", str(pass_output)]) == 0
    assert json.loads(pass_output.read_text(encoding="utf-8"))["passed"] is True

    run["methods"][2]["aggregates"]["3"]["recall_at_k"] = 0.0
    run_path.write_text(json.dumps(run), encoding="utf-8")
    assert main(["--config", str(GATE_PATH), "--run", str(run_path), "--output", str(fail_output)]) == 1
    assert json.loads(fail_output.read_text(encoding="utf-8"))["passed"] is False


def test_cli_rejects_non_finite_json_before_a_passing_decision(tmp_path: Path) -> None:
    run_path = tmp_path / "run.json"
    output = tmp_path / "result.json"
    run = _run()
    run["methods"][0]["aggregates"]["3"]["recall_at_k"] = float("nan")
    run_path.write_text(json.dumps(run), encoding="utf-8")

    assert main(["--config", str(GATE_PATH), "--run", str(run_path), "--output", str(output)]) == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["passed"] is False
    assert result["diagnostics"][0]["reason_code"] == "invalid_gate_or_run_contract"
