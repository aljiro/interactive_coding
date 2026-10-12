"""Entry point executed inside the sandbox container.

Reads  /inputs/manifest.json + /inputs/<name>.npy   (public features only)
Loads  /bundle/submission.py                        (student code)
Calls  predict(X) once per input dataset
Writes one JSON document to the *original* stdout; everything the student prints is
redirected to stderr so it cannot corrupt the result.

Each manifest entry carries an ``output`` spec describing what predict() must return:

    {"kind": "probabilities"}                          one P(class 1) per row  -> (N,)
    {"kind": "class_probabilities", "n_classes": K}    one row of K probabilities -> (N, K)
"""

import importlib.util
import json
import os
import sys
import time
import traceback

BUNDLE = "/bundle"
INPUTS = "/inputs"

_real_stdout = None


def _capture_stdout() -> None:
    """Keep the real stdout for the result; send everything else (even fd-level) to stderr."""
    global _real_stdout
    _real_stdout = os.fdopen(os.dup(1), "w", buffering=1)
    os.dup2(2, 1)  # fd-level: C extensions printing to fd 1 go to stderr as well
    sys.stdout = sys.stderr


def emit(obj) -> None:
    out = _real_stdout or sys.stdout
    out.write(json.dumps(obj, allow_nan=True))
    out.write("\n")
    out.flush()


def fail(error: str, tb: str | None = None) -> None:
    emit({"ok": False, "error": error[:1000], "traceback": (tb or "")[-4000:]})


class OutputError(ValueError):
    """predict() returned something of the wrong shape/type (a student-facing message)."""


def _to_numpy(out):
    import numpy as np

    if hasattr(out, "detach"):  # torch tensor
        out = out.detach().cpu().numpy()
    return np.asarray(out, dtype=np.float64)


def to_1d(out, n: int):
    """Binary case: (N,), (N,1) or predict_proba-style (N,2) -> (N,) with P(class 1)."""
    arr = _to_numpy(out)
    if arr.ndim == 2 and arr.shape[1] == 1:
        arr = arr[:, 0]
    elif arr.ndim == 2 and arr.shape[1] == 2 and arr.shape[0] == n:
        arr = arr[:, 1]  # predict_proba-style output: take P(class 1)
    return arr.reshape(-1)


def to_2d(out, n: int, k: int):
    """Multiclass case: (N, K) probabilities. Integer class labels (N,) are one-hot encoded."""
    import numpy as np

    arr = _to_numpy(out)
    if arr.ndim == 2 and arr.shape[1] == 1:
        arr = arr[:, 0]
    if arr.ndim == 1:
        if arr.shape[0] != n:
            raise OutputError(f"predict() returned {arr.shape[0]} values, expected {n}.")
        if not np.all(np.isfinite(arr)) or np.any(arr != np.round(arr)) or arr.min() < 0 or arr.max() >= k:
            raise OutputError(
                f"predict() returned a 1-D array; expected an (N, {k}) array of class "
                f"probabilities (or integer class labels in 0..{k - 1})."
            )
        onehot = np.zeros((n, k), dtype=np.float64)
        onehot[np.arange(n), arr.astype(int)] = 1.0
        return onehot
    if arr.ndim != 2 or arr.shape[1] != k:
        raise OutputError(
            f"predict() returned an array of shape {arr.shape}; expected ({n}, {k}) "
            f"class probabilities (one row per input, one column per class)."
        )
    return arr


def to_output(out, n: int, spec: dict):
    kind = (spec or {}).get("kind", "probabilities")
    if kind == "class_probabilities":
        return to_2d(out, n, int(spec["n_classes"]))
    if kind == "probabilities":
        return to_1d(out, n)
    raise OutputError(f"unknown output kind '{kind}' in manifest")


def main() -> None:
    _capture_stdout()
    try:
        import numpy as np

        with open(os.path.join(INPUTS, "manifest.json")) as fh:
            manifest = json.load(fh)
        os.chdir(BUNDLE)
        sys.path.insert(0, BUNDLE)
        timings = {}
        t0 = time.perf_counter()
        spec = importlib.util.spec_from_file_location("submission", os.path.join(BUNDLE, "submission.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        timings["import"] = round(time.perf_counter() - t0, 3)
        predict = getattr(module, "predict", None)
        if not callable(predict):
            fail("submission.py does not define a callable predict(X).")
            return
        predictions = {}
        for ds in manifest["datasets"]:
            X = np.load(os.path.join(INPUTS, ds["file"]))
            t1 = time.perf_counter()
            try:
                out = to_output(predict(X), ds["n"], ds.get("output"))
            except OutputError as exc:
                fail(f"dataset '{ds['name']}': {exc}")
                return
            timings[ds["name"]] = round(time.perf_counter() - t1, 3)
            if out.shape[0] != ds["n"]:
                fail(f"predict() returned {out.shape[0]} values for dataset '{ds['name']}', expected {ds['n']}.")
                return
            predictions[ds["name"]] = out.tolist()
        emit({"ok": True, "predictions": predictions, "timings": timings})
    except SyntaxError as exc:
        fail(f"SyntaxError in submission.py: {exc}", traceback.format_exc())
    except MemoryError:
        fail("MemoryError: the submission exceeded the memory limit.")
    except BaseException as exc:  # noqa: BLE001 - includes SystemExit from student code
        fail(f"{type(exc).__name__}: {exc}", traceback.format_exc())


if __name__ == "__main__":
    main()
