from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from app.services.evaluation.dataset import CASE_CATEGORIES, load_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "evaluation" / "datasets" / "retrieval-v1"
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "retrieval_benchmark_repo"


def test_versioned_dataset_validates_fixture_and_required_case_matrix() -> None:
    dataset = load_dataset(DATASET_ROOT, FIXTURE_ROOT)

    assert dataset.dataset_id == "retrieval-v1"
    assert dataset.dataset_revision.startswith("sha256:")
    assert dataset.fixture_revision == "sha256:535617ad5e9d94d55d1f4a627498e84f72a8caa0a9f87934962884a55e6b03c9"
    assert {case.category for case in dataset.cases} == CASE_CATEGORIES
    assert dataset.method_names == (
        "exact_keyword",
        "naive_semantic",
        "deterministic_hybrid",
    )
    assert any(not case.policy.should_answer for case in dataset.cases)
    assert all(case.fixture_revision == dataset.fixture_revision for case in dataset.cases)


def _mutable_copy(tmp_path: Path) -> tuple[Path, Path]:
    dataset_root = tmp_path / "dataset"
    fixture_root = tmp_path / "fixture"
    shutil.copytree(DATASET_ROOT, dataset_root)
    shutil.copytree(FIXTURE_ROOT, fixture_root)
    return dataset_root, fixture_root


def _change_cases(dataset_root: Path, mutate) -> None:
    cases_path = dataset_root / "cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    mutate(cases)
    cases_path.write_text(json.dumps(cases), encoding="utf-8")


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda cases: cases[0]["candidates"].append(dict(cases[0]["candidates"][0])), "duplicate candidate"),
        (lambda cases: cases[0]["candidates"][0].update(raw_score=float("nan")), "finite and positive"),
        (lambda cases: cases[0]["candidates"][0].update(source_path="../routes.py"), "fixture-relative"),
        (lambda cases: cases[0]["candidates"][0].update(end_line=999), "outside the fixture"),
        (lambda cases: cases[0]["candidates"][0].update(content_hash="sha256:" + "0" * 64), "stale source hash"),
        (lambda cases: cases[0].update(candidates=cases[0]["candidates"] * 200), "bounded to 500"),
    ],
)
def test_invalid_candidate_or_source_fails_before_scoring(tmp_path: Path, mutate, message: str) -> None:
    dataset_root, fixture_root = _mutable_copy(tmp_path)
    _change_cases(dataset_root, mutate)

    with pytest.raises(ValueError, match=message):
        load_dataset(dataset_root, fixture_root)


def test_changed_fixture_bytes_fail_the_declared_hash(tmp_path: Path) -> None:
    dataset_root, fixture_root = _mutable_copy(tmp_path)
    (fixture_root / "backend" / "routes.py").write_text("changed\n", encoding="utf-8")

    with pytest.raises(ValueError, match="content hash mismatch"):
        load_dataset(dataset_root, fixture_root)


def test_case_file_cannot_escape_dataset_root(tmp_path: Path) -> None:
    dataset_root, fixture_root = _mutable_copy(tmp_path)
    manifest_path = dataset_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["case_file"] = "../cases.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="normalized fixture-relative path"):
        load_dataset(dataset_root, fixture_root)
