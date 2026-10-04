"""Built-in submission adapters."""

from __future__ import annotations

from app.core.registry import Registry
from app.core.submission_adapter import SubmissionAdapter
from app.submissions.prediction_csv import PredictionCsvAdapter
from app.submissions.python_bundle import PythonBundleAdapter


def register_all(registry: Registry[SubmissionAdapter]) -> None:
    registry.register(PredictionCsvAdapter(), replace=True)
    registry.register(PythonBundleAdapter(), replace=True)
