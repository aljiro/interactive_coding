"""Visualization types describe the *structured display data* a frontend plugin receives.

The backend half (this class) decides what public data is stored per session and per
submission; the frontend half (``frontend/src/challenge-visualizations/<id>``) renders it.
Both are looked up by the same stable id.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, ClassVar

from app.core.submission_adapter import PredictionSet

if TYPE_CHECKING:
    from app.core.challenge import Challenge


class VisualizationType(ABC):
    id: ClassVar[str]
    label: ClassVar[str] = ""

    def session_display(self, challenge: Challenge) -> dict[str, Any]:
        """Static, public display data for a challenge (e.g. training points, axes)."""
        return challenge.display_data()

    def submission_display(
        self, predictions: PredictionSet, challenge: Challenge
    ) -> dict[str, Any]:
        """Per-submission public payload (e.g. a probability field). Must be JSON-serialisable."""
        return {}
