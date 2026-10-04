"""Generic challenge framework: registries and the three modular concerns.

* :mod:`app.core.submission_adapter` - what students upload and how it becomes predictions
* :mod:`app.core.evaluator`          - how predictions are scored against hidden targets
* :mod:`app.core.visualization`      - what structured display data the UI receives

A :class:`app.core.challenge.Challenge` wires implementations together by stable id.
"""

from app.core.challenge import Challenge, MetricSpec, Resource
from app.core.evaluator import EvaluationOutput, Evaluator
from app.core.registries import adapters, challenges, evaluators, visualizations
from app.core.registry import Registry, RegistryError
from app.core.submission_adapter import (
    AdapterContext,
    InputDataset,
    PredictionSet,
    SubmissionAdapter,
    SubmissionError,
    SubmissionTimeout,
)
from app.core.visualization import VisualizationType

__all__ = [
    "AdapterContext",
    "Challenge",
    "EvaluationOutput",
    "Evaluator",
    "InputDataset",
    "MetricSpec",
    "PredictionSet",
    "Registry",
    "RegistryError",
    "Resource",
    "SubmissionAdapter",
    "SubmissionError",
    "SubmissionTimeout",
    "VisualizationType",
    "adapters",
    "challenges",
    "evaluators",
    "visualizations",
]
