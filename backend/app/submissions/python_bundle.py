"""Python model bundle adapter: a ZIP with ``submission.py`` exposing ``predict(X)``.

Student code is *never* imported here. The bundle is extracted (safely), the public input
features are materialised as ``.npy`` files, and an isolated runner (see
:mod:`app.runners.docker_runner`) executes ``predict`` and returns plain predictions.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from app.core.submission_adapter import (
    AdapterContext,
    PredictionSet,
    SubmissionAdapter,
    SubmissionError,
)
from app.runners import get_runner
from app.submissions.zip_safety import safe_extract_zip

ENTRYPOINT = "submission.py"


class PythonBundleAdapter(SubmissionAdapter):
    id = "python_bundle"
    label = "Python model bundle (ZIP)"
    accepted_extensions = (".zip",)
    description = (
        "A ZIP archive containing submission.py (defining predict(X) -> probabilities) "
        "plus any weights/files it needs. It runs in an isolated container."
    )

    def run(self, artifact: Path, ctx: AdapterContext) -> PredictionSet:
        settings = ctx.settings
        bundle_root = ctx.workdir / "bundle"
        inputs_dir = ctx.workdir / "inputs"
        for d in (bundle_root, inputs_dir):
            if d.exists():
                shutil.rmtree(d)
        safe_extract_zip(
            artifact,
            bundle_root,
            max_files=settings.zip_max_files,
            max_total_uncompressed=settings.zip_max_uncompressed_bytes,
            max_ratio=settings.zip_max_compression_ratio,
        )
        bundle_dir = locate_bundle_dir(bundle_root)
        _make_world_readable(bundle_root)

        inputs_dir.mkdir(parents=True)
        spec = output_spec(ctx.challenge.adapter_config)
        manifest = {"datasets": []}
        for name, ds in ctx.inputs.items():
            np.save(inputs_dir / f"{name}.npy", np.ascontiguousarray(ds.X, dtype=np.float32))
            manifest["datasets"].append(
                {"name": name, "n": ds.n, "file": f"{name}.npy", "output": spec}
            )
        (inputs_dir / "manifest.json").write_text(json.dumps(manifest))
        _make_world_readable(inputs_dir)

        runner = get_runner(settings)
        result = runner.run(bundle_dir=bundle_dir, inputs_dir=inputs_dir, workdir=ctx.workdir)

        predictions: dict[str, np.ndarray] = {}
        problems: list[str] = []
        for name, ds in ctx.inputs.items():
            raw = result.predictions.get(name)
            if raw is None:
                problems.append(f"no predictions returned for dataset '{name}'")
                continue
            try:
                predictions[name] = validate_output(np.asarray(raw, dtype=np.float64), ds.n, spec)
            except ValueError as exc:
                problems.append(f"dataset '{name}': {exc}")
        if problems:
            raise SubmissionError("predict() output failed validation.", problems)

        info = {"source": "python_bundle", "runtime_seconds": result.runtime_seconds}
        if result.stderr_tail:
            info["stderr_tail"] = result.stderr_tail
        return PredictionSet(predictions, info=info)


def output_spec(adapter_config: dict) -> dict:
    """What predict() must return, as written into the sandbox manifest.

    ``{"kind": "probabilities"}`` (default): one P(class 1) per row -> (N,).
    ``{"kind": "class_probabilities", "n_classes": K}``: K probabilities per row -> (N, K).
    """
    spec = dict(adapter_config.get("output") or {"kind": "probabilities"})
    if spec.get("kind") == "class_probabilities":
        spec["n_classes"] = int(spec["n_classes"])
    return spec


def validate_output(arr: np.ndarray, n: int, spec: dict) -> np.ndarray:
    """Check shape/range of one dataset's predictions; raises ValueError with a student message."""
    kind = spec.get("kind", "probabilities")
    if kind == "class_probabilities":
        k = int(spec["n_classes"])
        if arr.ndim != 2 or arr.shape != (n, k):
            raise ValueError(
                f"predict() returned shape {arr.shape}, expected ({n}, {k}) class probabilities"
            )
    else:
        arr = arr.reshape(-1)
        if arr.shape[0] != n:
            raise ValueError(f"predict() returned {arr.shape[0]} values, expected {n}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("predictions contain NaN or Inf")
    if arr.min() < -1e-6 or arr.max() > 1.0 + 1e-6:
        hint = " (did you forget the softmax?)" if kind == "class_probabilities" else ""
        raise ValueError(
            f"probabilities must lie in [0, 1] (found min {arr.min():.3g}, "
            f"max {arr.max():.3g}){hint}"
        )
    arr = np.clip(arr, 0.0, 1.0)
    if kind == "class_probabilities":
        sums = arr.sum(axis=1)
        if np.any(np.abs(sums - 1.0) > 1e-2):
            raise ValueError(
                f"each row must be a probability distribution summing to 1 (found row sums "
                f"between {sums.min():.3g} and {sums.max():.3g}); apply softmax to the logits"
            )
        arr = arr / np.maximum(sums, 1e-12)[:, None]
    return arr


def locate_bundle_dir(root: Path) -> Path:
    """Return the directory containing submission.py (root, or a single top-level folder)."""
    if (root / ENTRYPOINT).is_file():
        return root
    entries = [p for p in root.iterdir() if not p.name.startswith("__MACOSX")]
    if len(entries) == 1 and entries[0].is_dir() and (entries[0] / ENTRYPOINT).is_file():
        return entries[0]
    listing = sorted(str(p.relative_to(root)) for p in root.rglob("*"))[:20]
    raise SubmissionError(
        f"ZIP archive must contain {ENTRYPOINT} at its top level.",
        ["Archive contents: " + (", ".join(listing) or "(empty)")],
    )


def _make_world_readable(path: Path) -> None:
    """The sandbox runs as an unprivileged uid; make the read-only inputs readable for it."""
    for p in path.rglob("*"):
        try:
            p.chmod(0o755 if p.is_dir() else 0o644)
        except OSError:
            pass
    path.chmod(0o755)
