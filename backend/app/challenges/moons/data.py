"""Deterministic Two-Moons data.

All datasets are generated with ``sklearn.datasets.make_moons`` and *fixed seeds*:

    training set   : 600 points, noise 0.22, random_state = 1
    hidden test set: 1000 points, noise 0.22, random_state = 2
    grid           : 100 x 100 points covering x1 in [-1.75, 2.75], x2 in [-1.25, 1.75]

The hidden test labels are never written to any public resource or mounted into runners.
"""

from __future__ import annotations

import io
from functools import lru_cache

import numpy as np
from sklearn.datasets import make_moons

N_TRAIN = 600
N_TEST = 1000
NOISE = 0.22
TRAIN_SEED = 1
TEST_SEED = 2
GRID_NX = 100
GRID_NY = 100
X1_RANGE = (-1.75, 2.75)
X2_RANGE = (-1.25, 1.75)


@lru_cache
def training_set() -> tuple[np.ndarray, np.ndarray]:
    X, y = make_moons(n_samples=N_TRAIN, noise=NOISE, random_state=TRAIN_SEED)
    return X.astype(np.float64), y.astype(np.int64)


@lru_cache
def hidden_test_set() -> tuple[np.ndarray, np.ndarray]:
    X, y = make_moons(n_samples=N_TEST, noise=NOISE, random_state=TEST_SEED)
    return X.astype(np.float64), y.astype(np.int64)


@lru_cache
def grid_points() -> np.ndarray:
    """(nx*ny, 2) grid, row-major with x1 varying fastest: id = iy * nx + ix."""
    xs = np.linspace(X1_RANGE[0], X1_RANGE[1], GRID_NX)
    ys = np.linspace(X2_RANGE[0], X2_RANGE[1], GRID_NY)
    gx, gy = np.meshgrid(xs, ys)
    return np.column_stack([gx.ravel(), gy.ravel()]).astype(np.float64)


def _csv(header: list[str], rows: np.ndarray, fmt: list[str]) -> bytes:
    buf = io.StringIO()
    buf.write(",".join(header) + "\n")
    for row in rows:
        buf.write(",".join(f.format(v) for f, v in zip(fmt, row, strict=True)) + "\n")
    return buf.getvalue().encode("utf-8")


def train_csv() -> bytes:
    X, y = training_set()
    rows = np.column_stack([np.arange(len(y)), X, y])
    return _csv(["id", "x1", "x2", "label"], rows, ["{:.0f}", "{:.6f}", "{:.6f}", "{:.0f}"])


def test_features_csv() -> bytes:
    X, _ = hidden_test_set()
    rows = np.column_stack([np.arange(len(X)), X])
    return _csv(["id", "x1", "x2"], rows, ["{:.0f}", "{:.6f}", "{:.6f}"])


def grid_csv() -> bytes:
    G = grid_points()
    rows = np.column_stack([np.arange(len(G)), G])
    return _csv(["id", "x1", "x2"], rows, ["{:.0f}", "{:.6f}", "{:.6f}"])


def sample_predictions_csv() -> bytes:
    """A syntactically valid (but useless) submission: constant 0.5 everywhere."""
    buf = io.StringIO()
    buf.write("dataset,id,probability\n")
    for i in range(N_TEST):
        buf.write(f"test,{i},0.5\n")
    for i in range(GRID_NX * GRID_NY):
        buf.write(f"grid,{i},0.5\n")
    return buf.getvalue().encode("utf-8")
