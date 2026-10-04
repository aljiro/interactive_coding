"""Declarative challenge definition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.submission_adapter import InputDataset


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    higher_is_better: bool = True
    format: str = ".3f"
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "higher_is_better": self.higher_is_better,
            "format": self.format,
            "description": self.description,
        }


@dataclass(frozen=True)
class Resource:
    """A public, downloadable challenge file. ``loader`` returns the bytes on demand."""

    name: str
    description: str
    loader: Callable[[], bytes]
    content_type: str = "text/csv"
    # Adapter ids this file is relevant for; None = relevant for every submission type.
    submission_types: tuple[str, ...] | None = None


@dataclass
class Challenge:
    id: str
    title: str
    short_description: str
    instructions_md: str
    submission_type: str  # SubmissionAdapter id
    evaluator: str  # Evaluator id
    visualization: str  # VisualizationType id
    primary_metric: MetricSpec
    # Public inputs students predict on, keyed by dataset name.
    inputs: Callable[[], dict[str, InputDataset]]
    # Hidden ground truth keyed by dataset name. Only the evaluator ever sees this.
    hidden_targets: Callable[[], dict[str, np.ndarray]]
    # Public data used by the visualization (training points, axes, ...).
    display_data: Callable[[], dict[str, Any]] = lambda: {}
    secondary_metrics: list[MetricSpec] = field(default_factory=list)
    resources: list[Resource] = field(default_factory=list)
    # Extra instructions shown only when that submission type is enabled for the session.
    submission_instructions_md: dict[str, str] = field(default_factory=dict)
    adapter_config: dict[str, Any] = field(default_factory=dict)
    evaluator_config: dict[str, Any] = field(default_factory=dict)
    visualization_config: dict[str, Any] = field(default_factory=dict)

    def get_resource(self, name: str) -> Resource | None:
        for r in self.resources:
            if r.name == name:
                return r
        return None

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "short_description": self.short_description,
            "submission_type": self.submission_type,
            "evaluator": self.evaluator,
            "visualization": self.visualization,
            "primary_metric": self.primary_metric.as_dict(),
            "secondary_metrics": [m.as_dict() for m in self.secondary_metrics],
        }

    def detail(self) -> dict[str, Any]:
        return {
            **self.summary(),
            "instructions_md": self.instructions_md,
            "resources": [
                {
                    "name": r.name,
                    "description": r.description,
                    "content_type": r.content_type,
                    "submission_types": list(r.submission_types) if r.submission_types else None,
                }
                for r in self.resources
            ],
            "submission_instructions_md": dict(self.submission_instructions_md),
            "visualization_config": self.visualization_config,
        }
