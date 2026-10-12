"""Declarative definition of the small-data MNIST "fix the training recipe" challenge."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app.challenges.mnist_small import data
from app.core.challenge import Challenge, MetricSpec, Resource
from app.core.submission_adapter import InputDataset

_HERE = Path(__file__).parent


def _inputs() -> dict[str, InputDataset]:
    X_test, _ = data.hidden_test_set()
    X_train, _ = data.training_set()
    return {
        "test": InputDataset("test", np.arange(len(X_test)), X_test),
        "train": InputDataset("train", np.arange(len(X_train)), X_train),
    }


def _hidden_targets() -> dict[str, np.ndarray]:
    _, y_test = data.hidden_test_set()
    _, y_train = data.training_set()
    return {"test": y_test, "train": y_train}


def _display_data() -> dict:
    X_train, _ = data.training_set()
    X_test, _ = data.hidden_test_set()
    return {
        "class_labels": [str(c) for c in range(data.N_CLASSES)],
        "image_shape": list(data.IMAGE_SHAPE),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "score_range": [0.0, 1.0],
        "sample_digits": data.sample_digits(),
    }


CHALLENGE = Challenge(
    id="mnist_small",
    title="Small-data MNIST — Fix the Training Recipe",
    short_description=(
        "1000 training digits, a naive baseline that barely learns. Make it train, then make it "
        "generalise: scored by accuracy on 5000 hidden test digits, with your train/test gap "
        "shown live on the projector."
    ),
    instructions_md=(_HERE / "instructions.md").read_text(encoding="utf-8"),
    submission_instructions_md={
        "python_bundle": (_HERE / "instructions_python_bundle.md").read_text(encoding="utf-8"),
    },
    submission_type="python_bundle",
    evaluator="multiclass_classification",
    visualization="generalization_arena",
    primary_metric=MetricSpec(
        key="accuracy", label="hidden test accuracy", higher_is_better=True, format=".3f"
    ),
    secondary_metrics=[
        MetricSpec("train_accuracy", "training accuracy", format=".3f"),
        MetricSpec("generalization_gap", "train − test gap", higher_is_better=False, format=".3f"),
        MetricSpec("log_loss", "log loss", higher_is_better=False, format=".3f"),
    ],
    inputs=_inputs,
    hidden_targets=_hidden_targets,
    display_data=_display_data,
    resources=[
        Resource(
            "mnist_train.csv",
            "Training digits: id, label, 784 raw pixel values (1000 rows)",
            data.train_csv,
        ),
        Resource(
            "submission_template.py",
            "Skeleton submission.py for the ZIP bundle",
            lambda: (_HERE / "submission_template.py").read_bytes(),
            content_type="text/x-python",
            submission_types=("python_bundle",),
        ),
    ],
    adapter_config={
        "allowed_submission_types": ["python_bundle"],
        "output": {"kind": "class_probabilities", "n_classes": data.N_CLASSES},
    },
    evaluator_config={"dataset": "test", "train_dataset": "train"},
    visualization_config={"test_dataset": "test", "train_dataset": "train", "n_mistakes": 12},
)
