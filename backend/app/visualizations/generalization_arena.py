"""Generalisation arena: train-vs-hidden-test accuracy scatter + per-submission error analysis.

Session display contract (produced by the challenge's ``display_data``)::

    {
      "class_labels": ["0", ..., "9"],
      "image_shape": [28, 28],
      "n_train": 1000, "n_test": 5000,
      "score_range": [0.0, 1.0],                       # axis range for both accuracies
      "sample_digits": [{"label": 3, "pixels": [...]}, ...]   # a few public training digits
    }

The cohort scatter itself needs no per-submission payload: it is drawn from each
participant's ``best_metrics`` (``train_accuracy`` on x, ``accuracy`` on y).

Submission display payload::

    {
      "test_accuracy": 0.91, "train_accuracy": 1.0,
      "confusion": [[...], ...],                 # K x K, rows = true class, cols = predicted
      "per_class_accuracy": [...],               # K values
      "mistakes": [{"index": i, "true": 3, "pred": 5, "confidence": 0.97, "pixels": [...]}, ...]
    }

``mistakes`` are the most *confident* errors on the hidden test set (the public test
features are inputs every submission already receives, so showing them reveals nothing).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.challenge import Challenge
from app.core.submission_adapter import PredictionSet
from app.core.visualization import VisualizationType


class GeneralizationArena(VisualizationType):
    id = "generalization_arena"
    label = "Train-vs-test accuracy arena with confusion matrix"

    def submission_display(
        self, predictions: PredictionSet, challenge: Challenge
    ) -> dict[str, Any]:
        cfg = challenge.visualization_config
        test_name = cfg.get("test_dataset", "test")
        train_name = cfg.get("train_dataset", "train")
        n_mistakes = int(cfg.get("n_mistakes", 12))
        targets = challenge.hidden_targets()

        p = np.asarray(predictions[test_name], dtype=np.float64)
        y = np.asarray(targets[test_name]).astype(int)
        k = p.shape[1]
        pred = p.argmax(axis=1)
        confusion = np.zeros((k, k), dtype=np.int64)
        np.add.at(confusion, (y, pred), 1)
        row_totals = np.maximum(confusion.sum(axis=1), 1)
        per_class = np.diag(confusion) / row_totals

        out: dict[str, Any] = {
            "test_accuracy": round(float(np.mean(pred == y)), 6),
            "confusion": confusion.tolist(),
            "per_class_accuracy": [round(float(v), 4) for v in per_class],
        }
        if train_name in predictions.predictions and train_name in targets:
            pt = np.asarray(predictions[train_name], dtype=np.float64)
            yt = np.asarray(targets[train_name]).astype(int)
            out["train_accuracy"] = round(float(np.mean(pt.argmax(axis=1) == yt)), 6)

        wrong = np.flatnonzero(pred != y)
        if len(wrong) and n_mistakes > 0:
            conf = p[wrong, pred[wrong]]
            order = wrong[np.argsort(-conf)][:n_mistakes]
            X_test = challenge.inputs()[test_name].X
            out["mistakes"] = [
                {
                    "index": int(i),
                    "true": int(y[i]),
                    "pred": int(pred[i]),
                    "confidence": round(float(p[i, pred[i]]), 4),
                    "pixels": np.clip(np.rint(X_test[i]), 0, 255).astype(int).tolist(),
                }
                for i in order
            ]
        else:
            out["mistakes"] = []
        return out
