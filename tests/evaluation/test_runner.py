from __future__ import annotations

import json
from pathlib import Path

from app.services.evaluation.dataset import content_digest, load_dataset
from app.services.evaluation.runner import main, run_evaluation


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "evaluation" / "datasets" / "retrieval-v1"
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "retrieval_benchmark_repo"


def _run():
    dataset = load_dataset(DATASET_ROOT, FIXTURE_ROOT)
    return run_evaluation(
        dataset,
        code_revision="EVA-001-test",
        index_version_id="idx_eva_001",
        started_at="2026-07-14T00:00:00Z",
        completed_at="2026-07-14T00:00:00Z",
    )


def test_run_is_reproducible_and_checksum_bound() -> None:
    first = _run()
    second = _run()

    assert first == second
    assert first["dataset_revision"] == "sha256:734b850ed37fcc2a7fa5aaf6f6903c2c1cbc3a5b85db68ecfa1cc024546ecc49"
    # The semantic checksum intentionally binds the declared code revision.
    assert first["semantic_checksum"] == "sha256:dabde69d2c0029ff7e655801621c77d8044246dea29e3b19284ad61377d10fc0"
    report_checksum = first.pop("report_checksum")
    assert report_checksum == content_digest(first)


def test_versioned_baseline_aggregates_are_reviewed_regression_values() -> None:
    report = _run()
    aggregates = {item["method"]: item["aggregates"]["3"] for item in report["methods"]}

    assert aggregates["exact_keyword"]["recall_at_k"] == 0.666666666667
    assert aggregates["naive_semantic"]["recall_at_k"] == 0.4
    assert aggregates["deterministic_hybrid"]["recall_at_k"] == 1.0
    assert aggregates["deterministic_hybrid"]["ndcg_at_k"] == 0.926185950714
    assert aggregates["naive_semantic"]["insufficient_evidence_correct"] == 1.0


def test_every_method_receives_identical_candidate_ids_per_case() -> None:
    report = _run()
    by_method = {
        method["method"]: {
            case["case_id"]: case["candidate_input_ids"] for case in method["cases"]
        }
        for method in report["methods"]
    }

    assert by_method["exact_keyword"] == by_method["naive_semantic"]
    assert by_method["exact_keyword"] == by_method["deterministic_hybrid"]
    assert report["threshold_decisions"] == []
    assert report["timing_mode"] == "not_measured"


def test_cli_writes_canonical_report(tmp_path: Path) -> None:
    output = tmp_path / "run.json"

    exit_code = main(
        [
            "--dataset",
            str(DATASET_ROOT),
            "--fixture-root",
            str(FIXTURE_ROOT),
            "--output",
            str(output),
            "--code-revision",
            "EVA-001-test",
            "--index-version",
            "idx_eva_001",
            "--started-at",
            "2026-07-14T00:00:00Z",
            "--completed-at",
            "2026-07-14T00:00:00Z",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "evaluation-run/v1"
    assert payload["provider"] == "deterministic-candidate-fixture"
