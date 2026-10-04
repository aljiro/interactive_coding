"""Process-wide registries. Built-ins are registered by :func:`app.plugins.load_builtin`."""

from __future__ import annotations

from app.core.challenge import Challenge
from app.core.evaluator import Evaluator
from app.core.registry import Registry, RegistryError
from app.core.submission_adapter import SubmissionAdapter
from app.core.visualization import VisualizationType

adapters: Registry[SubmissionAdapter] = Registry("submission adapter")
evaluators: Registry[Evaluator] = Registry("evaluator")
visualizations: Registry[VisualizationType] = Registry("visualization type")
challenges: Registry[Challenge] = Registry("challenge")


def validate_challenge(challenge: Challenge) -> None:
    """Fail fast if a challenge references components that are not registered."""
    missing = []
    if challenge.submission_type not in adapters:
        missing.append(f"submission adapter '{challenge.submission_type}'")
    if challenge.evaluator not in evaluators:
        missing.append(f"evaluator '{challenge.evaluator}'")
    if challenge.visualization not in visualizations:
        missing.append(f"visualization '{challenge.visualization}'")
    if missing:
        raise RegistryError(f"challenge '{challenge.id}' references unknown " + ", ".join(missing))


def register_challenge(challenge: Challenge, *, replace: bool = False) -> Challenge:
    validate_challenge(challenge)
    return challenges.register(challenge, replace=replace)
