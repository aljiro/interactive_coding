"""Declarative definition of the Moons reference challenge."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app.challenges.moons import data
from app.core.challenge import Challenge, MetricSpec, Resource
from app.core.submission_adapter import InputDataset

_HERE = Path(__file__).parent


def _inputs() -> dict[str, InputDataset]:
    X_test, _ = data.hidden_test_set()
    G = data.grid_points()
    return {
        "test": InputDataset("test", np.arange(len(X_test)), X_test),
        "grid": InputDataset("grid", np.arange(len(G)), G),
    }


def _hidden_targets() -> dict[str, np.ndarray]:
    _, y_test = data.hidden_test_set()
    return {"test": y_test}


def _display_data() -> dict:
    X, y = data.training_set()
    return {
        "points": {
            "x": [round(float(v), 4) for v in X[:, 0]],
            "y": [round(float(v), 4) for v in X[:, 1]],
            "label": [int(v) for v in y],
        },
        "grid": {
            "nx": data.GRID_NX,
            "ny": data.GRID_NY,
            "x0": data.X1_RANGE[0],
            "x1": data.X1_RANGE[1],
            "y0": data.X2_RANGE[0],
            "y1": data.X2_RANGE[1],
        },
        "axis_labels": ["x₁", "x₂"],
        "class_labels": ["class 0", "class 1"],
        "score_range": [0.5, 1.0],
    }


CHALLENGE = Challenge(
    id="moons",
    title="Two Moons — Decision Boundary Challenge",
    short_description=(
        "Classify the two interleaving half-moons. Scored by accuracy on 1000 hidden test "
        "points; your decision surface is shown live on the projector."
    ),
    instructions_md=(_HERE / "instructions.md").read_text(encoding="utf-8"),
    submission_instructions_md={
        "prediction_csv": (_HERE / "instructions_prediction_csv.md").read_text(encoding="utf-8"),
        "python_bundle": (_HERE / "instructions_python_bundle.md").read_text(encoding="utf-8"),
    },
    submission_type="python_bundle",
    evaluator="binary_classification",
    visualization="decision_boundary_arena",
    primary_metric=MetricSpec(
        key="accuracy", label="hidden test accuracy", higher_is_better=True, format=".3f"
    ),
    secondary_metrics=[
        MetricSpec("log_loss", "log loss", higher_is_better=False, format=".3f"),
        MetricSpec("brier", "Brier score", higher_is_better=False, format=".3f"),
        MetricSpec("n_predictions", "predictions", format="d"),
    ],
    inputs=_inputs,
    hidden_targets=_hidden_targets,
    display_data=_display_data,
    resources=[
        Resource("train.csv", "Training features and labels (600 points)", data.train_csv),
        Resource(
            "test_features.csv",
            "Hidden-test features (1000 points, no labels)",
            data.test_features_csv,
        ),
        Resource("visualization_grid.csv", "Dense 100×100 visualisation grid", data.grid_csv),
        Resource(
            "sample_predictions.csv",
            "Format example: a constant 0.5 submission",
            data.sample_predictions_csv,
            submission_types=("prediction_csv",),
        ),
        Resource(
            "submission_template.py",
            "Skeleton submission.py for the ZIP bundle",
            lambda: (_HERE / "submission_template.py").read_bytes(),
            content_type="text/x-python",
            submission_types=("python_bundle",),
        ),
    ],
    # Students may upload either artifact type; the adapter is chosen by file extension.
    adapter_config={"allowed_submission_types": ["prediction_csv", "python_bundle"]},
    evaluator_config={"dataset": "test", "threshold": 0.5},
    visualization_config={"grid_dataset": "grid"},
)
