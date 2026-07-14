from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import fmean
from typing import Any, Sequence

from app.services.evaluation.dataset import EvaluationDataset, content_digest, load_dataset
from app.services.evaluation.methods import EvaluationMethod, evaluate_method
from app.services.evaluation.metrics import score_retrieval


RUN_SCHEMA = "evaluation-run/v1"


def _aggregate(case_results: list[dict[str, Any]], k_values: tuple[int, ...]) -> dict[str, Any]:
    aggregates: dict[str, Any] = {}
    metric_names = (
        "recall_at_k",
        "precision_at_k",
        "reciprocal_rank",
        "ndcg_at_k",
        "source_diversity",
        "duplicate_rate",
        "insufficient_evidence_correct",
    )
    for k in k_values:
        by_k = [item["metrics"][str(k)] for item in case_results]
        aggregate_metrics: dict[str, float | None] = {}
        for name in metric_names:
            values = [metric[name] for metric in by_k if metric[name] is not None]
            aggregate_metrics[name] = round(fmean(values), 12) if values else None
        aggregates[str(k)] = aggregate_metrics
    return aggregates


def run_evaluation(
    dataset: EvaluationDataset,
    *,
    code_revision: str,
    index_version_id: str,
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    if not code_revision.strip():
        raise ValueError("code_revision must not be blank")
    if not index_version_id.startswith("idx_"):
        raise ValueError("index_version_id must use the idx_ prefix")
    if not started_at.strip() or not completed_at.strip():
        raise ValueError("run timestamps must not be blank")

    method_outputs: list[dict[str, Any]] = []
    method_config_ids: dict[str, str] = {}
    for method_name in dataset.method_names:
        method = EvaluationMethod(method_name)
        case_outputs: list[dict[str, Any]] = []
        for case in sorted(dataset.cases, key=lambda item: item.id):
            method_result = evaluate_method(
                method,
                case,
                repository_id=dataset.repository_id,
                index_version_id=index_version_id,
            )
            method_config_ids[method.value] = method_result.method_config_id
            metrics = {
                str(k): score_retrieval(
                    method_result.results,
                    case.expected.relevant_entity_keys,
                    k=k,
                    should_answer=case.policy.should_answer,
                ).as_dict()
                for k in dataset.k_values
            }
            case_outputs.append(
                {
                    "case_id": case.id,
                    "category": case.category,
                    "candidate_input_ids": sorted(item.candidate_id for item in case.candidates),
                    "status": method_result.status,
                    "error_code": method_result.error_code,
                    "results": [item.as_dict() for item in method_result.results],
                    "metrics": metrics,
                    "duration_ms": None,
                    "tokens": None,
                    "provider_cost": None,
                }
            )
        method_outputs.append(
            {
                "method": method.value,
                "method_config_id": method_config_ids[method.value],
                "cases": case_outputs,
                "aggregates": _aggregate(case_outputs, dataset.k_values),
            }
        )

    raw_results_checksum = content_digest(method_outputs)
    semantic_payload = {
        "schema_version": RUN_SCHEMA,
        "dataset_id": dataset.dataset_id,
        "dataset_revision": dataset.dataset_revision,
        "fixture_id": dataset.fixture_id,
        "fixture_revision": dataset.fixture_revision,
        "code_revision": code_revision,
        "repository_id": dataset.repository_id,
        "index_version_id": index_version_id,
        "method_config_ids": method_config_ids,
        "seed": 0,
        "temperature": 0,
        "capacity_profile": "synthetic-small",
        "concurrency": 1,
        "cache_condition": "disabled",
        "provider": "deterministic-candidate-fixture",
        "budget_configuration": {"k_values": list(dataset.k_values)},
        "raw_results_checksum": raw_results_checksum,
        "methods": method_outputs,
    }
    semantic_checksum = content_digest(semantic_payload)
    report: dict[str, Any] = {
        **semantic_payload,
        "started_at": started_at,
        "completed_at": completed_at,
        "timing_mode": "not_measured",
        "semantic_checksum": semantic_checksum,
        "threshold_decisions": [],
        "limitations": [
            "Semantic candidates are deterministic fixture observations, not measured embedding-provider quality.",
            "Latency, token, cost, answer-quality, and release thresholds are not established by EVA-001.",
        ],
    }
    report["report_checksum"] = content_digest(report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic EVA-001 retrieval benchmark")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=Path("tests/fixtures/retrieval_benchmark_repo"),
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--index-version", required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--completed-at", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    dataset = load_dataset(arguments.dataset, arguments.fixture_root)
    report = run_evaluation(
        dataset,
        code_revision=arguments.code_revision,
        index_version_id=arguments.index_version,
        started_at=arguments.started_at,
        completed_at=arguments.completed_at,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
