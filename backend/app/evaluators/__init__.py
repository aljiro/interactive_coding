from __future__ import annotations

from app.core.evaluator import Evaluator
from app.core.registry import Registry
from app.evaluators.binary_classification import BinaryClassificationEvaluator


def register_all(registry: Registry[Evaluator]) -> None:
    registry.register(BinaryClassificationEvaluator(), replace=True)
