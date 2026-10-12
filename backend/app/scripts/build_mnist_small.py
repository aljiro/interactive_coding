"""Build the committed ``mnist_small.npz`` from the four original MNIST idx files.

    python -m app.scripts.build_mnist_small --src /path/with/idx-gz-files

Selection is deterministic (fixed seed):

    training set   : 1000 digits from the official MNIST *training* split, 100 per class
    hidden test set: 5000 digits from the official MNIST *test* split, 500 per class

The resulting archive (uint8 pixels + labels + the original indices) is stored next to the
challenge definition and is the only artefact the server needs. It is regenerated only when
the selection rule changes; ``tests/test_mnist_small.py`` checks its shape and balance.
"""

from __future__ import annotations

import argparse
import gzip
import struct
from pathlib import Path

import numpy as np

SEED = 20261012
N_TRAIN_PER_CLASS = 100
N_TEST_PER_CLASS = 500
FILES = {
    "train_images": "train-images-idx3-ubyte.gz",
    "train_labels": "train-labels-idx1-ubyte.gz",
    "test_images": "t10k-images-idx3-ubyte.gz",
    "test_labels": "t10k-labels-idx1-ubyte.gz",
}
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "challenges" / "mnist_small" / "mnist_small.npz"


def read_idx(path: Path) -> np.ndarray:
    with gzip.open(path, "rb") as fh:
        magic, n = struct.unpack(">II", fh.read(8))
        kind = magic & 0xFF
        if kind == 1:  # labels
            return np.frombuffer(fh.read(n), dtype=np.uint8)
        if kind == 3:  # images
            rows, cols = struct.unpack(">II", fh.read(8))
            return np.frombuffer(fh.read(n * rows * cols), dtype=np.uint8).reshape(n, rows * cols)
    raise ValueError(f"{path}: unknown idx magic {magic:#x}")


def stratified_subset(y: np.ndarray, per_class: int, rng: np.random.Generator) -> np.ndarray:
    idx = []
    for c in range(10):
        pool = np.flatnonzero(y == c)
        idx.append(rng.choice(pool, size=per_class, replace=False))
    idx = np.concatenate(idx)
    rng.shuffle(idx)
    return idx


def build(src: Path) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(SEED)
    Xtr = read_idx(src / FILES["train_images"])
    ytr = read_idx(src / FILES["train_labels"])
    Xte = read_idx(src / FILES["test_images"])
    yte = read_idx(src / FILES["test_labels"])
    tr = stratified_subset(ytr, N_TRAIN_PER_CLASS, rng)
    te = stratified_subset(yte, N_TEST_PER_CLASS, rng)
    return {
        "X_train": Xtr[tr],
        "y_train": ytr[tr].astype(np.int64),
        "train_index": tr.astype(np.int64),
        "X_test": Xte[te],
        "y_test": yte[te].astype(np.int64),
        "test_index": te.astype(np.int64),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--src", type=Path, required=True, help="directory with the 4 idx .gz files"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    arrays = build(args.src)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out, **arrays)
    print(f"wrote {args.out} ({args.out.stat().st_size} bytes)")
    for k, v in arrays.items():
        print(f"  {k}: {v.shape} {v.dtype}")


if __name__ == "__main__":
    main()
