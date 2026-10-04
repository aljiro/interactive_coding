"""Entry point executed inside the sandbox container.

Reads  /inputs/manifest.json + /inputs/<name>.npy   (public features only)
Loads  /bundle/submission.py                        (student code)
Calls  predict(X) once per input dataset
Writes one JSON document to the *original* stdout; everything the student prints is
redirected to stderr so it cannot corrupt the result.
"""

import importlib.util
import json
import os
import sys
import time
import traceback

BUNDLE = "/bundle"
INPUTS = "/inputs"

_real_stdout = os.fdopen(os.dup(1), "w", buffering=1)
os.dup2(2, 1)  # fd-level: C extensions printing to fd 1 go to stderr as well
sys.stdout = sys.stderr


def emit(obj) -> None:
    _real_stdout.write(json.dumps(obj, allow_nan=True))
    _real_stdout.write("\n")
    _real_stdout.flush()


def fail(error: str, tb: str | None = None) -> None:
    emit({"ok": False, "error": error[:1000], "traceback": (tb or "")[-4000:]})


def to_1d(out, n: int):
    import numpy as np

    if hasattr(out, "detach"):  # torch tensor
        out = out.detach().cpu().numpy()
    arr = np.asarray(out, dtype=np.float64)
    if arr.ndim == 2 and arr.shape[1] == 1:
        arr = arr[:, 0]
    elif arr.ndim == 2 and arr.shape[1] == 2 and arr.shape[0] == n:
        arr = arr[:, 1]  # predict_proba-style output: take P(class 1)
    return arr.reshape(-1)


def main() -> None:
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
            out = to_1d(predict(X), ds["n"])
            timings[ds["name"]] = round(time.perf_counter() - t1, 3)
            if out.shape[0] != ds["n"]:
                fail(f"predict() returned {out.shape[0]} values for dataset '{ds['name']}', expected {ds['n']}.")
                return
            predictions[ds["name"]] = [float(v) for v in out]
        emit({"ok": True, "predictions": predictions, "timings": timings})
    except SyntaxError as exc:
        fail(f"SyntaxError in submission.py: {exc}", traceback.format_exc())
    except MemoryError:
        fail("MemoryError: the submission exceeded the memory limit.")
    except BaseException as exc:  # noqa: BLE001 - includes SystemExit from student code
        fail(f"{type(exc).__name__}: {exc}", traceback.format_exc())


if __name__ == "__main__":
    main()
