"""Evaluators score a :class:`PredictionSet` against hidden targets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

import numpy as np

from app.core.submission_adapter import PredictionSet


@dataclass
class EvaluationOutput:
    primary_score: float
    metrics: dict[str, Any] = field(default_factory=dict)


class Evaluator(ABC):
    id: ClassVar[str]
    label: ClassVar[str] = ""

    @abstractmethod
    def evaluate(
        self,
        predictions: PredictionSet,
        targets: dict[str, np.ndarray],
        config: dict[str, Any],
    ) -> EvaluationOutput: ...
