from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
from math import ceil
import os
from pathlib import Path
import platform
from statistics import fmean
from time import perf_counter
from typing import Any, Sequence

from app.services.evaluation.dataset import (
    CandidateObservation,
    EvaluationCase,
    EvaluationDataset,
    content_digest,
    load_dataset,
)
from app.services.evaluation.methods import (
    EvaluationMethod,
    EvaluationResultItem,
    evaluate_method,
)
from app.services.evaluation.metrics import score_retrieval
from app.services.evaluation.ollama_embeddings import (
    MAX_EMBED_INPUTS,
    EmbeddingModelIdentity,
    ModelMemory,
    OllamaEmbeddingClient,
    cosine_similarity,
)


RUN_SCHEMA = "ollama-embedding-benchmark/v1"
METHODS = ("sparse", "ollama_dense", "sparse_dense_hybrid")
RRF_K = 60
SPARSE_WEIGHT = 2.0
DENSE_WEIGHT = 1.0
MAX_QUERY_P95_MS = 2_000.0
MAX_CORPUS_EMBED_MS = 30_000.0
MAX_MODEL_MEMORY_BYTES = 2 * 1024**3
MIN_QUALITY_GAIN = 0.01


def _candidate_corpus(dataset: EvaluationDataset) -> dict[str, CandidateObservation]:
    corpus: dict[str, CandidateObservation] = {}
    for case in dataset.cases:
        for candidate in case.candidates:
            previous = corpus.setdefault(candidate.candidate_id, candidate)
            if previous != candidate:
                raise ValueError("candidate identity maps to inconsistent observations")
    return dict(sorted(corpus.items()))


def _embed_corpus(
    client: OllamaEmbeddingClient,
    corpus: dict[str, CandidateObservation],
) -> tuple[dict[str, tuple[float, ...]], int, float, int]:
    candidate_ids = tuple(corpus)
    vectors: dict[str, tuple[float, ...]] = {}
    dimension: int | None = None
    provider_duration_ns = 0
    started = perf_counter()
    for offset in range(0, len(candidate_ids), MAX_EMBED_INPUTS):
        batch_ids = candidate_ids[offset : offset + MAX_EMBED_INPUTS]
        batch = client.embed(tuple(corpus[item].chunk_content for item in batch_ids))
        dimension = dimension or batch.dimension
        if batch.dimension != dimension:
            raise ValueError("embedding dimension changed within one corpus build")
        vectors.update(zip(batch_ids, batch.vectors, strict=True))
        provider_duration_ns += batch.total_duration_ns or 0
    return vectors, dimension or 0, round((perf_counter() - started) * 1000, 6), provider_duration_ns


def _dense_items(
    case: EvaluationCase,
    query_vector: tuple[float, ...],
    corpus_vectors: dict[str, tuple[float, ...]],
) -> tuple[EvaluationResultItem, ...]:
    scored = [
        (
            cosine_similarity(query_vector, corpus_vectors[candidate.candidate_id]),
            candidate,
        )
        for candidate in case.candidates
    ]
    scored.sort(key=lambda item: (-item[0], item[1].entity_key, item[1].candidate_id))
    return tuple(
        EvaluationResultItem(
            entity_key=candidate.entity_key,
            source_key=candidate.source_key,
            start_line=candidate.start_line,
            end_line=candidate.end_line,
            candidate_ids=(candidate.candidate_id,),
            retrievers=("ollama_dense",),
            score=score,
        )
        for score, candidate in scored[: case.budgets.max_results]
    )


def _hybrid_items(
    sparse: tuple[EvaluationResultItem, ...],
    dense: tuple[EvaluationResultItem, ...],
    limit: int,
) -> tuple[EvaluationResultItem, ...]:
    keyed: dict[tuple[str, str, int, int], dict[str, object]] = {}
    for method, weight, items in (
        ("sparse", SPARSE_WEIGHT, sparse),
        ("ollama_dense", DENSE_WEIGHT, dense),
    ):
        for rank, item in enumerate(items, start=1):
            key = (item.entity_key, item.source_key, item.start_line, item.end_line)
            state = keyed.setdefault(
                key,
                {"candidate_ids": set(), "retrievers": set(), "score": 0.0},
            )
            state["candidate_ids"].update(item.candidate_ids)  # type: ignore[union-attr]
            state["retrievers"].add(method)  # type: ignore[union-attr]
            state["score"] = float(state["score"]) + weight / (RRF_K + rank)
    ordered = sorted(keyed.items(), key=lambda item: (-float(item[1]["score"]), item[0]))
    return tuple(
        EvaluationResultItem(
            entity_key=key[0],
            source_key=key[1],
            start_line=key[2],
            end_line=key[3],
            candidate_ids=tuple(sorted(state["candidate_ids"])),  # type: ignore[arg-type]
            retrievers=tuple(sorted(state["retrievers"])),  # type: ignore[arg-type]
            score=round(float(state["score"]), 12),
        )
        for key, state in ordered[:limit]
    )


def _aggregate(case_results: list[dict[str, Any]], k_values: tuple[int, ...]) -> dict[str, Any]:
    metrics = (
        "recall_at_k",
        "precision_at_k",
        "reciprocal_rank",
        "ndcg_at_k",
        "source_diversity",
        "duplicate_rate",
        "insufficient_evidence_correct",
    )
    output: dict[str, Any] = {}
    for k in k_values:
        by_k = [item["metrics"][str(k)] for item in case_results]
        output[str(k)] = {
            name: (
                round(fmean(values), 12)
                if (values := [item[name] for item in by_k if item[name] is not None])
                else None
            )
            for name in metrics
        }
    return output


def _method_config_ids(model: EmbeddingModelIdentity) -> dict[str, str]:
    configurations = {
        "sparse": {"method": "exact_keyword", "source": "EVA-001"},
        "ollama_dense": {
            "method": "cosine_top_k",
            "model": model.resolved_model,
            "digest": model.digest,
            "truncate": False,
        },
        "sparse_dense_hybrid": {
            "method": "weighted_rrf",
            "rrf_k": RRF_K,
            "sparse_weight": SPARSE_WEIGHT,
            "dense_weight": DENSE_WEIGHT,
        },
    }
    return {
        name: f"ret004cfg_{content_digest(value).removeprefix('sha256:')[:24]}"
        for name, value in configurations.items()
    }


def _percentile_95(values: list[float]) -> float:
    if not values:
        raise ValueError("p95 requires at least one observation")
    ordered = sorted(values)
    return round(ordered[max(0, ceil(0.95 * len(ordered)) - 1)], 6)


def _mean_quality(repetitions: list[dict[str, Any]], k: str = "3") -> dict[str, Any]:
    output: dict[str, Any] = {}
    for method in METHODS:
        aggregates = [item["methods"][method]["aggregates"][k] for item in repetitions]
        output[method] = {
            name: (
                round(fmean(values), 12)
                if (values := [item[name] for item in aggregates if item[name] is not None])
                else None
            )
            for name in aggregates[0]
        }
    return output


def _adoption_decision(
    quality: dict[str, Any],
    *,
    query_p95_ms: float,
    corpus_embed_max_ms: float,
    memory: ModelMemory,
) -> dict[str, Any]:
    sparse = quality["sparse"]
    hybrid = quality["sparse_dense_hybrid"]
    checks = {
        "recall_at_3_no_regression": hybrid["recall_at_k"] >= sparse["recall_at_k"],
        "reciprocal_rank_no_regression": hybrid["reciprocal_rank"] >= sparse["reciprocal_rank"],
        "insufficient_evidence_no_regression": hybrid["insufficient_evidence_correct"]
        >= sparse["insufficient_evidence_correct"],
        "minimum_quality_gain": max(
            hybrid["recall_at_k"] - sparse["recall_at_k"],
            hybrid["reciprocal_rank"] - sparse["reciprocal_rank"],
        )
        >= MIN_QUALITY_GAIN,
        "query_p95_within_budget": query_p95_ms <= MAX_QUERY_P95_MS,
        "corpus_embedding_within_budget": corpus_embed_max_ms <= MAX_CORPUS_EMBED_MS,
        "model_memory_observed": memory.observed_bytes is not None,
        "model_memory_within_budget": memory.observed_bytes is not None
        and memory.observed_bytes <= MAX_MODEL_MEMORY_BYTES,
    }
    accepted = all(checks.values())
    return {
        "decision": "adopt_for_ret_005" if accepted else "do_not_adopt",
        "accepted": accepted,
        "checks": checks,
        "policy": {
            "minimum_quality_gain": MIN_QUALITY_GAIN,
            "max_query_p95_ms": MAX_QUERY_P95_MS,
            "max_corpus_embedding_ms": MAX_CORPUS_EMBED_MS,
            "max_model_memory_bytes": MAX_MODEL_MEMORY_BYTES,
        },
    }


def run_benchmark(
    dataset: EvaluationDataset,
    client: OllamaEmbeddingClient,
    *,
    repetitions: int,
    code_revision: str,
    index_version_id: str,
    started_at: str,
    completed_at: str | None,
) -> dict[str, Any]:
    if not 3 <= repetitions <= 10:
        raise ValueError("benchmark repetitions must be in [3, 10]")
    if not code_revision.strip() or not index_version_id.startswith("idx_"):
        raise ValueError("benchmark run identity is invalid")
    model = client.identity()
    corpus = _candidate_corpus(dataset)
    if not corpus:
        raise ValueError("benchmark corpus is empty")
    method_config_ids = _method_config_ids(model)
    repetition_outputs: list[dict[str, Any]] = []
    all_query_latencies: list[float] = []
    dimensions: set[int] = set()

    for repetition in range(1, repetitions + 1):
        corpus_vectors, dimension, corpus_ms, corpus_provider_ns = _embed_corpus(client, corpus)
        dimensions.add(dimension)
        method_cases: dict[str, list[dict[str, Any]]] = {method: [] for method in METHODS}
        query_latencies: list[float] = []
        query_provider_ns = 0
        for case in sorted(dataset.cases, key=lambda item: item.id):
            query_started = perf_counter()
            query_batch = client.embed((case.question,))
            query_ms = round((perf_counter() - query_started) * 1000, 6)
            if query_batch.dimension != dimension:
                raise ValueError("query and corpus embedding dimensions differ")
            query_latencies.append(query_ms)
            all_query_latencies.append(query_ms)
            query_provider_ns += query_batch.total_duration_ns or 0

            sparse = evaluate_method(
                EvaluationMethod.EXACT_KEYWORD,
                case,
                repository_id=dataset.repository_id,
                index_version_id=index_version_id,
            ).results
            dense = _dense_items(case, query_batch.vectors[0], corpus_vectors)
            hybrid = _hybrid_items(sparse, dense, case.budgets.max_results)
            for method, results in zip(METHODS, (sparse, dense, hybrid), strict=True):
                method_cases[method].append(
                    {
                        "case_id": case.id,
                        "category": case.category,
                        "candidate_input_ids": sorted(item.candidate_id for item in case.candidates),
                        "results": [item.as_dict() for item in results],
                        "metrics": {
                            str(k): score_retrieval(
                                results,
                                case.expected.relevant_entity_keys,
                                k=k,
                                should_answer=case.policy.should_answer,
                            ).as_dict()
                            for k in dataset.k_values
                        },
                        "query_embedding_ms": query_ms if method != "sparse" else 0.0,
                    }
                )
        repetition_outputs.append(
            {
                "repetition": repetition,
                "corpus_embedding_ms": corpus_ms,
                "query_latency_p95_ms": _percentile_95(query_latencies),
                "provider_duration_ns": corpus_provider_ns + query_provider_ns,
                "methods": {
                    method: {
                        "method_config_id": method_config_ids[method],
                        "cases": method_cases[method],
                        "aggregates": _aggregate(method_cases[method], dataset.k_values),
                    }
                    for method in METHODS
                },
            }
        )

    if len(dimensions) != 1:
        raise ValueError("embedding dimension changed across repetitions")
    memory = client.memory()
    quality = _mean_quality(repetition_outputs)
    query_p95 = _percentile_95(all_query_latencies)
    corpus_max = max(item["corpus_embedding_ms"] for item in repetition_outputs)
    decision = _adoption_decision(
        quality,
        query_p95_ms=query_p95,
        corpus_embed_max_ms=corpus_max,
        memory=memory,
    )
    semantic_payload: dict[str, Any] = {
        "schema_version": RUN_SCHEMA,
        "dataset_id": dataset.dataset_id,
        "dataset_revision": dataset.dataset_revision,
        "fixture_id": dataset.fixture_id,
        "fixture_revision": dataset.fixture_revision,
        "repository_id": dataset.repository_id,
        "index_version_id": index_version_id,
        "code_revision": code_revision,
        "provider": "ollama-local",
        "model": asdict(model),
        "embedding_dimension": next(iter(dimensions)),
        "preprocessing": {
            "schema_version": "ret-004-preprocessing/v1",
            "candidate_text": "exact chunk_content UTF-8",
            "query_text": "exact case question UTF-8",
            "truncate": False,
            "similarity": "cosine",
            "batch_limit": MAX_EMBED_INPUTS,
        },
        "method_config_ids": method_config_ids,
        "repetitions": repetition_outputs,
        "summary": {
            "quality_at_3": quality,
            "query_latency_p95_ms": query_p95,
            "corpus_embedding_max_ms": corpus_max,
            "model_memory": asdict(memory),
            "model_memory_observed_bytes": memory.observed_bytes,
            "provider_cost": 0,
        },
        "adoption": decision,
        "capacity_profile": {
            "os": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "logical_cpu_count": os.cpu_count(),
            "concurrency": 1,
        },
    }
    semantic_payload["raw_results_checksum"] = content_digest(repetition_outputs)
    report: dict[str, Any] = {
        **semantic_payload,
        "started_at": started_at,
        "completed_at": completed_at or datetime.now(UTC).isoformat(),
        "limitations": [
            "The six-case synthetic EVA-001 dataset is a benchmark foundation, not a production release threshold.",
            "Ollama process memory is the bounded /api/ps snapshot; host-wide peak RSS and energy are not measured.",
            "This task records an RET-005 adoption decision but does not change production retrieval or indexing.",
        ],
    }
    report["report_checksum"] = content_digest(report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the RET-004 local Ollama embedding benchmark")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--fixture-root", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--index-version", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    started_at = datetime.now(UTC).isoformat()
    dataset = load_dataset(arguments.dataset, arguments.fixture_root)
    client = OllamaEmbeddingClient(
        base_url=arguments.base_url,
        model=arguments.model,
        timeout_seconds=arguments.timeout_seconds,
    )
    report = run_benchmark(
        dataset,
        client,
        repetitions=arguments.repetitions,
        code_revision=arguments.code_revision,
        index_version_id=arguments.index_version,
        started_at=started_at,
        completed_at=None,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
