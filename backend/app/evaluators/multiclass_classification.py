"""Multiclass classification evaluator: accuracy (primary), log loss, train/test gap.

Predictions are ``(N, K)`` class-probability rows. If the challenge also exposes its public
training set as an input dataset (``config["train_dataset"]``), accuracy on it is reported
as ``train_accuracy`` together with the generalisation gap ``train_accuracy - accuracy``.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.evaluator import EvaluationOutput, Evaluator
from app.core.submission_adapter import PredictionSet, SubmissionError

EPS = 1e-7


def _check(predictions: PredictionSet, targets: dict[str, np.ndarray], name: str) -> tuple:
    if name not in predictions.predictions:
        raise SubmissionError(f"No predictions for the evaluation dataset '{name}'.")
    p = np.asarray(predictions[name], dtype=np.float64)
    y = np.asarray(targets[name]).astype(int)
    if p.ndim != 2 or p.shape[0] != y.shape[0]:
        raise SubmissionError(
            f"Prediction shape {p.shape} does not match {y.shape[0]} targets with K classes."
        )
    return p, y


def accuracy(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(p.argmax(axis=1) == y))


def log_loss(p: np.ndarray, y: np.ndarray, eps: float = EPS) -> float:
    p = np.clip(p, eps, 1.0)
    return float(-np.mean(np.log(p[np.arange(len(y)), y])))


class MulticlassClassificationEvaluator(Evaluator):
    id = "multiclass_classification"
    label = "Multiclass classification (accuracy / log loss / train-test gap)"

    def evaluate(
        self, predictions: PredictionSet, targets: dict[str, np.ndarray], config: dict[str, Any]
    ) -> EvaluationOutput:
        dataset = config.get("dataset", "test")
        p, y = _check(predictions, targets, dataset)
        acc = accuracy(p, y)
        metrics: dict[str, Any] = {
            "accuracy": round(acc, 6),
            "log_loss": round(log_loss(p, y), 6),
        }
        train = config.get("train_dataset")
        if train and train in predictions.predictions and train in targets:
            pt, yt = _check(predictions, targets, train)
            train_acc = accuracy(pt, yt)
            metrics["train_accuracy"] = round(train_acc, 6)
            metrics["generalization_gap"] = round(train_acc - acc, 6)
        metrics["n_predictions"] = int(sum(len(v) for v in predictions.predictions.values()))
        return EvaluationOutput(primary_score=acc, metrics=metrics)
