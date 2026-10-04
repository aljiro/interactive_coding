"""Isolated execution of student code. Only the Docker runner executes anything."""

from __future__ import annotations

from app.runners.base import Runner, RunnerResult


def get_runner(settings) -> Runner:  # noqa: ANN001 - avoid import cycle with config
    from app.runners.docker_runner import DockerRunner

    return DockerRunner(settings)


__all__ = ["Runner", "RunnerResult", "get_runner"]
