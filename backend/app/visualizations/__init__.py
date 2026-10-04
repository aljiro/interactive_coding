from __future__ import annotations

from app.core.registry import Registry
from app.core.visualization import VisualizationType
from app.visualizations.decision_boundary_arena import DecisionBoundaryArena


def register_all(registry: Registry[VisualizationType]) -> None:
    registry.register(DecisionBoundaryArena(), replace=True)
