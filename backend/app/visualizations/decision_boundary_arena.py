"""Decision-boundary arena: 2-D dataset + probability field per submission + score blobs.

Session display contract (produced by the challenge's ``display_data``)::

    {
      "points": {"x": [...], "y": [...], "label": [...]},      # public training points
      "grid": {"nx": 100, "ny": 100, "x0": .., "x1": .., "y0": .., "y1": ..},
      "axis_labels": ["x1", "x2"],
      "class_labels": ["class 0", "class 1"],
      "score_range": [0.5, 1.0]
    }

Submission display payload::

    {"grid_probabilities": [p_0, ..., p_{nx*ny-1}]}   # row-major, x varies fastest
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.challenge import Challenge
from app.core.submission_adapter import PredictionSet
from app.core.visualization import VisualizationType


class DecisionBoundaryArena(VisualizationType):
    id = "decision_boundary_arena"
    label = "Decision boundary + score arena"

    def submission_display(
        self, predictions: PredictionSet, challenge: Challenge
    ) -> dict[str, Any]:
        grid_name = challenge.visualization_config.get("grid_dataset", "grid")
        probs = np.asarray(predictions[grid_name], dtype=np.float64)
        return {"grid_probabilities": [round(float(v), 4) for v in probs]}
