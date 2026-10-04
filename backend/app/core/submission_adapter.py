"""Submission adapters turn an uploaded artifact into a :class:`PredictionSet`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.challenge import Challenge


class SubmissionError(Exception):
    """A user-facing failure: the message and details are shown to the student."""

    status = "failed"

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class SubmissionTimeout(SubmissionError):
    status = "timed_out"


@dataclass
class InputDataset:
    """A named, public input dataset students must predict on (e.g. "test", "grid")."""

    name: str
    ids: np.ndarray  # shape (N,), integer ids as distributed to students
    X: np.ndarray  # shape (N, D) features

    @property
    def n(self) -> int:
        return int(self.ids.shape[0])


@dataclass
class PredictionSet:
    """Predictions per input dataset, aligned with ``InputDataset.ids`` order."""

    predictions: dict[str, np.ndarray]
    info: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, name: str) -> np.ndarray:
        return self.predictions[name]


@dataclass
class AdapterContext:
    challenge: Challenge
    inputs: dict[str, InputDataset]
    workdir: Path
    settings: Settings


class SubmissionAdapter(ABC):
    """Parses/validates one kind of artifact and produces predictions.

    Implementations must never execute untrusted code in-process; delegate to a runner.
    """

    id: ClassVar[str]
    label: ClassVar[str]
    accepted_extensions: ClassVar[tuple[str, ...]]
    description: ClassVar[str] = ""

    @abstractmethod
    def run(self, artifact: Path, ctx: AdapterContext) -> PredictionSet: ...

    def public_info(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "accepted_extensions": list(self.accepted_extensions),
            "description": self.description,
        }
