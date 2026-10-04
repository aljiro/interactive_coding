from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class RunnerResult:
    predictions: dict[str, list[float]]
    runtime_seconds: float = 0.0
    stderr_tail: str = ""
    info: dict[str, Any] = field(default_factory=dict)


class Runner(Protocol):
    def run(self, *, bundle_dir: Path, inputs_dir: Path, workdir: Path) -> RunnerResult: ...
