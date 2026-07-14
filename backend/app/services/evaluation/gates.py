from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from math import isfinite
from pathlib import Path
from typing import Any, Sequence

from app.services.evaluation.dataset import content_digest
from app.services.evaluation.methods import EvaluationMethod
from app.services.evaluation.runner import RUN_SCHEMA


GATE_SCHEMA = "evaluation-gate/v1"
GATE_RESULT_SCHEMA = "evaluation-gate-result/v1"
GATE_CLASSIFICATION = "ci_regression_only"
MAX_GATE_JSON_BYTES = 1_000_000
MAX_GATE_RULES = 100
CONTROLLED_METRICS = frozenset(
    {
        "recall_at_k",
        "precision_at_k",
        "reciprocal_rank",
        "ndcg_at_k",
        "source_diversity",
        "duplicate_rate",
        "insufficient_evidence_correct",
    }
)
CONTROLLED_COMPARISONS = frozenset({"gte", "lte", "eq"})


def _non_empty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _sha256(value: Any, field: str) -> str:
    digest = _non_empty(value, field)
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise ValueError(f"{field} must be a full sha256 identity")
    return digest


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{field} must be finite")
    return float(value)


@dataclass(frozen=True)
class MetricRule:
    rule_id: str
    method: EvaluationMethod
    k: int
    metric: str
    comparison: str
    bound: float

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("gate rule_id must not be blank")
        if not isinstance(self.method, EvaluationMethod):
            raise ValueError("gate method must be controlled")
        if self.k <= 0:
            raise ValueError("gate k must be positive")
        if self.metric not in CONTROLLED_METRICS:
            raise ValueError("gate metric must be controlled")
        if self.comparison not in CONTROLLED_COMPARISONS:
            raise ValueError("gate comparison must be controlled")
        if not isfinite(self.bound):
            raise ValueError("gate bound must be finite")

    def as_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "method": self.method.value,
            "k": self.k,
            "metric": self.metric,
            "comparison": self.comparison,
            "bound": self.bound,
        }


@dataclass(frozen=True)
class GateConfiguration:
    dataset_id: str
    dataset_revision: str
    fixture_id: str
    fixture_revision: str
    raw_results_checksum: str
    provider: str
    capacity_profile: str
    method_config_ids: tuple[tuple[EvaluationMethod, str], ...]
    rules: tuple[MetricRule, ...]
    schema_version: str = GATE_SCHEMA
    classification: str = GATE_CLASSIFICATION

    def __post_init__(self) -> None:
        if self.schema_version != GATE_SCHEMA:
            raise ValueError("unsupported evaluation gate schema")
        if self.classification != GATE_CLASSIFICATION:
            raise ValueError("evaluation gate must be classified ci_regression_only")
        if not self.dataset_id.strip() or not self.fixture_id.strip():
            raise ValueError("gate dataset and fixture IDs are required")
        _sha256(self.dataset_revision, "dataset_revision")
        _sha256(self.fixture_revision, "fixture_revision")
        _sha256(self.raw_results_checksum, "raw_results_checksum")
        if not self.provider.strip() or not self.capacity_profile.strip():
            raise ValueError("gate provider and capacity profile are required")
        methods = [method for method, _ in self.method_config_ids]
        if len(methods) != len(set(methods)) or set(methods) != set(EvaluationMethod):
            raise ValueError("gate must declare every evaluation method exactly once")
        if any(not config_id.strip() for _, config_id in self.method_config_ids):
            raise ValueError("gate method configuration IDs must not be blank")
        if not self.rules or len(self.rules) > MAX_GATE_RULES:
            raise ValueError(f"gate must contain between 1 and {MAX_GATE_RULES} rules")
        rule_ids = [rule.rule_id for rule in self.rules]
        coordinates = [(rule.method, rule.k, rule.metric) for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)) or len(coordinates) != len(set(coordinates)):
            raise ValueError("gate rules must have unique IDs and metric coordinates")

    @property
    def config_id(self) -> str:
        return f"evalgate_{content_digest(self.as_dict()).removeprefix('sha256:')[:24]}"

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "classification": self.classification,
            "run_identity": {
                "dataset_id": self.dataset_id,
                "dataset_revision": self.dataset_revision,
                "fixture_id": self.fixture_id,
                "fixture_revision": self.fixture_revision,
                "raw_results_checksum": self.raw_results_checksum,
                "provider": self.provider,
                "capacity_profile": self.capacity_profile,
                "method_config_ids": {
                    method.value: config_id
                    for method, config_id in sorted(self.method_config_ids, key=lambda item: item[0].value)
                },
            },
            "rules": [rule.as_dict() for rule in sorted(self.rules, key=lambda item: item.rule_id)],
        }


@dataclass(frozen=True)
class GateDiagnostic:
    rule_id: str
    passed: bool
    reason_code: str
    expected: str | float | None
    actual: str | float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "passed": self.passed,
            "reason_code": self.reason_code,
            "expected": self.expected,
            "actual": self.actual,
        }


def _load_json(path: Path) -> Any:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError(f"evaluation gate JSON is unavailable: {path}") from exc
    if size > MAX_GATE_JSON_BYTES:
        raise ValueError(f"evaluation gate JSON exceeds {MAX_GATE_JSON_BYTES} bytes: {path}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON value: {value}")),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid evaluation gate JSON: {path}") from exc


def load_gate_configuration(path: Path) -> GateConfiguration:
    raw = _load_json(path)
    if not isinstance(raw, dict):
        raise ValueError("evaluation gate configuration must be an object")
    identity = raw.get("run_identity")
    raw_rules = raw.get("rules")
    if not isinstance(identity, dict) or not isinstance(raw_rules, list):
        raise ValueError("evaluation gate requires run_identity and rules")
    raw_method_ids = identity.get("method_config_ids")
    if not isinstance(raw_method_ids, dict):
        raise ValueError("gate method_config_ids must be an object")
    try:
        method_config_ids = tuple(
            (EvaluationMethod(method), _non_empty(config_id, "method config ID"))
            for method, config_id in raw_method_ids.items()
        )
        rules = tuple(
            MetricRule(
                rule_id=_non_empty(item.get("rule_id"), "rule_id"),
                method=EvaluationMethod(item.get("method")),
                k=item.get("k") if isinstance(item.get("k"), int) else 0,
                metric=_non_empty(item.get("metric"), "metric"),
                comparison=_non_empty(item.get("comparison"), "comparison"),
                bound=_finite_number(item.get("bound"), "bound"),
            )
            for item in raw_rules
            if isinstance(item, dict)
        )
    except ValueError as exc:
        raise ValueError("invalid controlled evaluation gate value") from exc
    if len(rules) != len(raw_rules):
        raise ValueError("gate rule entries must be objects")
    return GateConfiguration(
        schema_version=raw.get("schema_version"),
        classification=raw.get("classification"),
        dataset_id=_non_empty(identity.get("dataset_id"), "dataset_id"),
        dataset_revision=_sha256(identity.get("dataset_revision"), "dataset_revision"),
        fixture_id=_non_empty(identity.get("fixture_id"), "fixture_id"),
        fixture_revision=_sha256(identity.get("fixture_revision"), "fixture_revision"),
        raw_results_checksum=_sha256(identity.get("raw_results_checksum"), "raw_results_checksum"),
        provider=_non_empty(identity.get("provider"), "provider"),
        capacity_profile=_non_empty(identity.get("capacity_profile"), "capacity_profile"),
        method_config_ids=method_config_ids,
        rules=rules,
    )


def _identity_diagnostic(rule_id: str, expected: str, actual: Any) -> GateDiagnostic:
    passed = isinstance(actual, str) and actual == expected
    return GateDiagnostic(
        rule_id=f"identity:{rule_id}",
        passed=passed,
        reason_code="identity_match" if passed else "identity_mismatch",
        expected=expected,
        actual=actual if isinstance(actual, str) else None,
    )


def _metric_passes(actual: float, comparison: str, bound: float) -> bool:
    if comparison == "gte":
        return actual >= bound
    if comparison == "lte":
        return actual <= bound
    return actual == bound


def evaluate_gate(configuration: GateConfiguration, run: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(run, dict) or run.get("schema_version") != RUN_SCHEMA:
        raise ValueError("unsupported evaluation run schema")
    diagnostics = [
        _identity_diagnostic("dataset_id", configuration.dataset_id, run.get("dataset_id")),
        _identity_diagnostic("dataset_revision", configuration.dataset_revision, run.get("dataset_revision")),
        _identity_diagnostic("fixture_id", configuration.fixture_id, run.get("fixture_id")),
        _identity_diagnostic("fixture_revision", configuration.fixture_revision, run.get("fixture_revision")),
        _identity_diagnostic("provider", configuration.provider, run.get("provider")),
        _identity_diagnostic("capacity_profile", configuration.capacity_profile, run.get("capacity_profile")),
    ]
    methods = run.get("methods")
    if not isinstance(methods, list):
        raise ValueError("evaluation run methods must be a list")
    recomputed_raw_checksum = content_digest(methods)
    diagnostics.append(
        _identity_diagnostic(
            "raw_results_checksum",
            configuration.raw_results_checksum,
            run.get("raw_results_checksum"),
        )
    )
    diagnostics.append(
        _identity_diagnostic(
            "raw_results_integrity",
            recomputed_raw_checksum,
            run.get("raw_results_checksum"),
        )
    )
    by_method: dict[str, dict[str, Any]] = {}
    for item in methods:
        if not isinstance(item, dict) or not isinstance(item.get("method"), str):
            raise ValueError("evaluation run method entries must be controlled objects")
        if item["method"] in by_method:
            raise ValueError("evaluation run contains duplicate methods")
        by_method[item["method"]] = item

    for method, config_id in configuration.method_config_ids:
        method_run = by_method.get(method.value)
        actual_config_id = method_run.get("method_config_id") if method_run else None
        diagnostics.append(
            _identity_diagnostic(f"method_config:{method.value}", config_id, actual_config_id)
        )
        cases = method_run.get("cases") if method_run else None
        completed = bool(cases) and isinstance(cases, list) and all(
            isinstance(case, dict)
            and case.get("status") == "completed"
            and case.get("error_code") is None
            for case in cases
        )
        diagnostics.append(
            GateDiagnostic(
                rule_id=f"method:{method.value}:cases_completed",
                passed=completed,
                reason_code="cases_completed" if completed else "missing_or_errored_cases",
                expected="completed",
                actual="completed" if completed else "invalid",
            )
        )

    for rule in configuration.rules:
        method_run = by_method.get(rule.method.value)
        aggregates = method_run.get("aggregates") if method_run else None
        by_k = aggregates.get(str(rule.k)) if isinstance(aggregates, dict) else None
        actual_value = by_k.get(rule.metric) if isinstance(by_k, dict) else None
        if isinstance(actual_value, bool) or not isinstance(actual_value, (int, float)):
            diagnostics.append(
                GateDiagnostic(rule.rule_id, False, "metric_missing_or_undefined", rule.bound, None)
            )
            continue
        actual = float(actual_value)
        if not isfinite(actual):
            diagnostics.append(GateDiagnostic(rule.rule_id, False, "metric_non_finite", rule.bound, None))
            continue
        passed = _metric_passes(actual, rule.comparison, rule.bound)
        diagnostics.append(
            GateDiagnostic(
                rule_id=rule.rule_id,
                passed=passed,
                reason_code="metric_passed" if passed else "metric_regression",
                expected=rule.bound,
                actual=actual,
            )
        )

    ordered = tuple(sorted(diagnostics, key=lambda item: item.rule_id))
    decision_payload = {
        "schema_version": GATE_RESULT_SCHEMA,
        "classification": configuration.classification,
        "gate_config_id": configuration.config_id,
        "run_semantic_checksum": run.get("semantic_checksum"),
        "passed": all(item.passed for item in ordered),
        "diagnostics": [item.as_dict() for item in ordered],
    }
    return {**decision_payload, "semantic_checksum": content_digest(decision_payload)}


def _failure_result(reason: str) -> dict[str, Any]:
    payload = {
        "schema_version": GATE_RESULT_SCHEMA,
        "classification": GATE_CLASSIFICATION,
        "gate_config_id": None,
        "run_semantic_checksum": None,
        "passed": False,
        "diagnostics": [
            GateDiagnostic("gate_contract", False, reason, "valid", "invalid").as_dict()
        ],
    }
    return {**payload, "semantic_checksum": content_digest(payload)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply the deterministic EVA-002 CI regression gate")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        configuration = load_gate_configuration(arguments.config)
        raw_run = _load_json(arguments.run)
        if not isinstance(raw_run, dict):
            raise ValueError("evaluation run must be an object")
        result = evaluate_gate(configuration, raw_run)
    except ValueError:
        result = _failure_result("invalid_gate_or_run_contract")
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    failures = [item["rule_id"] for item in result["diagnostics"] if not item["passed"]]
    if failures:
        print(f"EVA-002 gate FAILED: {', '.join(failures)}")
        return 1
    print(f"EVA-002 gate PASSED: {result['gate_config_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
