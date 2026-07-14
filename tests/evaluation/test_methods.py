from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.services.evaluation.dataset import load_dataset
from app.services.evaluation.methods import EvaluationMethod, evaluate_method


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _dataset():
    return load_dataset(
        PROJECT_ROOT / "evaluation" / "datasets" / "retrieval-v1",
        PROJECT_ROOT / "tests" / "fixtures" / "retrieval_benchmark_repo",
    )


def test_methods_use_same_inputs_and_expose_content_addressed_configuration() -> None:
    dataset = _dataset()
    case = next(item for item in dataset.cases if item.id == "semantic-token-purpose")

    results = {
        method: evaluate_method(
            method,
            case,
            repository_id=dataset.repository_id,
            index_version_id="idx_eva_001",
        )
        for method in EvaluationMethod
    }

    assert all(result.status == "completed" for result in results.values())
    assert all(result.method_config_id for result in results.values())
    assert results[EvaluationMethod.NAIVE_SEMANTIC].results[0].entity_key == "symbol:v1:create_access_token"
    assert results[EvaluationMethod.EXACT_KEYWORD].results[0].entity_key == "document:v1:authentication-flow"
    assert {item.entity_key for item in results[EvaluationMethod.DETERMINISTIC_HYBRID].results} == {
        "document:v1:authentication-flow",
        "symbol:v1:create_access_token",
    }


def test_method_results_are_invariant_to_candidate_input_order() -> None:
    dataset = _dataset()
    case = next(item for item in dataset.cases if item.id == "exact-login-route")
    reversed_case = replace(case, candidates=tuple(reversed(case.candidates)))

    for method in EvaluationMethod:
        first = evaluate_method(method, case, repository_id=dataset.repository_id, index_version_id="idx_eva_001")
        second = evaluate_method(method, reversed_case, repository_id=dataset.repository_id, index_version_id="idx_eva_001")
        assert first == second
