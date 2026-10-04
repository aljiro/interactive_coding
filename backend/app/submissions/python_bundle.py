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
        "A ZIP archive containing submission.py (defining predict(X) -> probabilities of "
        "class 1) plus any weights/files it needs. It runs in an isolated container."
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
        manifest = {"datasets": []}
        for name, ds in ctx.inputs.items():
            np.save(inputs_dir / f"{name}.npy", np.ascontiguousarray(ds.X, dtype=np.float32))
            manifest["datasets"].append({"name": name, "n": ds.n, "file": f"{name}.npy"})
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
            arr = np.asarray(raw, dtype=np.float64).reshape(-1)
            if arr.shape[0] != ds.n:
                problems.append(
                    f"dataset '{name}': predict() returned {arr.shape[0]} values, expected {ds.n}"
                )
                continue
            if not np.all(np.isfinite(arr)):
                problems.append(f"dataset '{name}': predictions contain NaN or Inf")
                continue
            if arr.min() < 0.0 or arr.max() > 1.0:
                problems.append(
                    f"dataset '{name}': probabilities must lie in [0, 1] "
                    f"(found min {arr.min():.3g}, max {arr.max():.3g})"
                )
                continue
            predictions[name] = arr
        if problems:
            raise SubmissionError("predict() output failed validation.", problems)

        info = {"source": "python_bundle", "runtime_seconds": result.runtime_seconds}
        if result.stderr_tail:
            info["stderr_tail"] = result.stderr_tail
        return PredictionSet(predictions, info=info)


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
