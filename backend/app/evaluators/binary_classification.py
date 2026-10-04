"""Binary classification evaluator: accuracy (primary), log loss, Brier score."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.evaluator import EvaluationOutput, Evaluator
from app.core.submission_adapter import PredictionSet, SubmissionError

EPS = 1e-7


def accuracy(p: np.ndarray, y: np.ndarray, threshold: float = 0.5) -> float:
    return float(np.mean((p >= threshold).astype(int) == y.astype(int)))


def log_loss(p: np.ndarray, y: np.ndarray, eps: float = EPS) -> float:
    p = np.clip(p, eps, 1.0 - eps)
    y = y.astype(np.float64)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y.astype(np.float64)) ** 2))


class BinaryClassificationEvaluator(Evaluator):
    id = "binary_classification"
    label = "Binary classification (accuracy / log loss)"

    def evaluate(
        self, predictions: PredictionSet, targets: dict[str, np.ndarray], config: dict[str, Any]
    ) -> EvaluationOutput:
        dataset = config.get("dataset", "test")
        if dataset not in predictions.predictions:
            raise SubmissionError(f"No predictions for the evaluation dataset '{dataset}'.")
        p = np.asarray(predictions[dataset], dtype=np.float64)
        y = np.asarray(targets[dataset])
        if p.shape != y.shape:
            raise SubmissionError(
                f"Prediction count {p.shape[0]} does not match target count {y.shape[0]}."
            )
        acc = accuracy(p, y, float(config.get("threshold", 0.5)))
        metrics = {
            "accuracy": round(acc, 6),
            "log_loss": round(log_loss(p, y), 6),
            "brier": round(brier(p, y), 6),
            "n_predictions": int(sum(len(v) for v in predictions.predictions.values())),
        }
        return EvaluationOutput(primary_score=acc, metrics=metrics)
