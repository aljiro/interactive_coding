"""Small-data MNIST.

    training set   : 1000 digits (100 per class) from the official MNIST training split
    hidden test set: 5000 digits (500 per class) from the official MNIST test split

Both are stored in ``mnist_small.npz`` next to this file (uint8 pixels, labels, and the indices
into the original splits). The archive is produced by ``app.scripts.build_mnist_small`` with
a fixed seed. Pixels are served *raw* (0..255) on purpose: input scaling is one of the things
students have to get right.
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

import numpy as np

ARCHIVE = Path(__file__).with_name("mnist_small.npz")
IMAGE_SHAPE = (28, 28)
N_CLASSES = 10
N_SAMPLE_DIGITS = 40


@lru_cache
def _arrays() -> dict[str, np.ndarray]:
    with np.load(ARCHIVE) as z:
        return {k: z[k] for k in z.files}


@lru_cache
def training_set() -> tuple[np.ndarray, np.ndarray]:
    a = _arrays()
    return a["X_train"].astype(np.float32), a["y_train"].astype(np.int64)


@lru_cache
def hidden_test_set() -> tuple[np.ndarray, np.ndarray]:
    a = _arrays()
    return a["X_test"].astype(np.float32), a["y_test"].astype(np.int64)


def train_csv() -> bytes:
    """``id,label,p0,...,p783`` with raw uint8 pixel values (row-major 28x28)."""
    X, y = training_set()
    buf = io.StringIO()
    buf.write("id,label," + ",".join(f"p{i}" for i in range(X.shape[1])) + "\n")
    Xi = X.astype(np.int64)
    for i, (row, label) in enumerate(zip(Xi, y, strict=True)):
        buf.write(f"{i},{int(label)}," + ",".join(map(str, row.tolist())) + "\n")
    return buf.getvalue().encode("utf-8")


def sample_digits(n: int = N_SAMPLE_DIGITS) -> list[dict]:
    """A few public training digits (one row per class first) for the projector."""
    X, y = training_set()
    picked: list[int] = []
    for c in range(N_CLASSES):
        picked.extend(np.flatnonzero(y == c)[: max(1, n // N_CLASSES)].tolist())
    return [{"label": int(y[i]), "pixels": np.rint(X[i]).astype(int).tolist()} for i in picked[:n]]
