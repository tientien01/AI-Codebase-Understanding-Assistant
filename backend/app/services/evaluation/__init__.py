"""Deterministic, provider-free evaluation contracts and runner."""

from app.services.evaluation.dataset import EvaluationDataset, load_dataset
from app.services.evaluation.metrics import RetrievalMetrics, score_retrieval
from app.services.evaluation.methods import EvaluationMethod, evaluate_method

__all__ = [
    "EvaluationDataset",
    "EvaluationMethod",
    "RetrievalMetrics",
    "evaluate_method",
    "load_dataset",
    "score_retrieval",
]
