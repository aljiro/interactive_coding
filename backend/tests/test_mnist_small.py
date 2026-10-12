"""Small-data MNIST challenge: data, multiclass output handling, evaluator and visualization."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from app.core import PredictionSet, challenges, evaluators, visualizations
from app.submissions.python_bundle import output_spec, validate_output

RUNNER = Path(__file__).resolve().parents[2] / "runner-images" / "python-ml" / "run_submission.py"


@pytest.fixture
def mnist():
    return challenges.get("mnist_small")


def _good_predictions(mnist, noise: float = 0.0, seed: int = 0) -> PredictionSet:
    """Near-perfect probabilities built from the hidden labels (tests only)."""
    rng = np.random.default_rng(seed)
    out = {}
    for name, y in mnist.hidden_targets().items():
        p = np.full((len(y), 10), 0.01)
        p[np.arange(len(y)), y] = 0.91
        if noise:
            flip = rng.random(len(y)) < noise
            wrong = (y + rng.integers(1, 10, len(y))) % 10
            p[flip] = 0.01
            p[np.flatnonzero(flip), wrong[flip]] = 0.91
        out[name] = p
    return PredictionSet(out)


def test_data_is_balanced_and_raw_pixels(mnist):
    inputs = mnist.inputs()
    targets = mnist.hidden_targets()
    assert inputs["train"].X.shape == (1000, 784) and inputs["test"].X.shape == (5000, 784)
    assert inputs["train"].X.max() == 255 and inputs["train"].X.min() == 0
    assert np.bincount(targets["train"]).tolist() == [100] * 10
    assert np.bincount(targets["test"]).tolist() == [500] * 10


def test_train_csv_round_trips(mnist):
    csv = mnist.get_resource("mnist_train.csv").loader().decode()
    lines = csv.splitlines()
    assert lines[0].startswith("id,label,p0,") and lines[0].endswith(",p783")
    assert len(lines) == 1001
    first = np.array(lines[1].split(","), dtype=np.int64)
    X, y = mnist.inputs()["train"].X, mnist.hidden_targets()["train"]
    assert first[0] == 0 and first[1] == y[0]
    np.testing.assert_array_equal(first[2:], X[0].astype(np.int64))


def test_output_spec_and_validation(mnist):
    spec = output_spec(mnist.adapter_config)
    assert spec == {"kind": "class_probabilities", "n_classes": 10}
    assert output_spec({}) == {"kind": "probabilities"}

    good = np.full((5, 10), 0.1)
    np.testing.assert_allclose(validate_output(good, 5, spec), good)
    with pytest.raises(ValueError, match=r"expected \(5, 10\)"):
        validate_output(np.zeros(5), 5, spec)
    with pytest.raises(ValueError, match="softmax"):
        validate_output(np.full((5, 10), 3.0), 5, spec)  # logits, not probabilities
    with pytest.raises(ValueError, match="sum"):
        validate_output(np.full((5, 10), 0.5), 5, spec)
    with pytest.raises(ValueError, match="NaN"):
        bad = good.copy()
        bad[0, 0] = np.nan
        validate_output(bad, 5, spec)
    # binary behaviour unchanged
    assert validate_output(np.array([[0.2], [0.9]]), 2, {"kind": "probabilities"}).shape == (2,)


def _harness():
    spec = importlib.util.spec_from_file_location("run_submission", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sandbox_harness_shapes_outputs():
    h = _harness()
    spec = {"kind": "class_probabilities", "n_classes": 10}
    probs = np.full((4, 10), 0.1)
    assert h.to_output(probs, 4, spec).shape == (4, 10)
    assert h.to_output(probs.tolist(), 4, spec).shape == (4, 10)
    onehot = h.to_output(np.array([3, 1, 4, 1]), 4, spec)  # integer class labels
    assert onehot.shape == (4, 10) and onehot.argmax(axis=1).tolist() == [3, 1, 4, 1]
    with pytest.raises(h.OutputError, match=r"expected \(4, 10\)"):
        h.to_output(np.zeros((4, 3)), 4, spec)
    with pytest.raises(h.OutputError):
        h.to_output(np.array([0.5, 0.5, 0.5, 0.5]), 4, spec)  # floats, not labels
    # binary path still works
    assert h.to_output(
        np.array([[0.2, 0.8], [0.6, 0.4]]), 2, {"kind": "probabilities"}
    ).tolist() == [0.8, 0.4]
    assert h.to_output([0.1, 0.2], 2, None).shape == (2,)


def test_multiclass_evaluator(mnist):
    ev = evaluators.get(mnist.evaluator)
    perfect = ev.evaluate(_good_predictions(mnist), mnist.hidden_targets(), mnist.evaluator_config)
    assert perfect.primary_score == 1.0
    assert perfect.metrics["train_accuracy"] == 1.0 and perfect.metrics["generalization_gap"] == 0.0
    assert abs(perfect.metrics["log_loss"] - (-np.log(0.91))) < 1e-6
    assert perfect.metrics["n_predictions"] == 6000

    noisy = ev.evaluate(
        _good_predictions(mnist, noise=0.2), mnist.hidden_targets(), mnist.evaluator_config
    )
    assert 0.75 < noisy.primary_score < 0.85
    assert noisy.metrics["accuracy"] == noisy.primary_score

    uniform = PredictionSet(
        {k: np.full((len(v), 10), 0.1) for k, v in mnist.hidden_targets().items()}
    )
    out = ev.evaluate(uniform, mnist.hidden_targets(), mnist.evaluator_config)
    assert abs(out.metrics["log_loss"] - np.log(10)) < 1e-6


def test_generalization_arena_display(mnist):
    viz = visualizations.get(mnist.visualization)
    session = viz.session_display(mnist)
    assert session["class_labels"] == [str(i) for i in range(10)]
    assert session["n_train"] == 1000 and session["n_test"] == 5000
    assert len(session["sample_digits"]) == 40 and len(session["sample_digits"][0]["pixels"]) == 784

    disp = viz.submission_display(_good_predictions(mnist, noise=0.1), mnist)
    conf = np.array(disp["confusion"])
    assert conf.shape == (10, 10) and conf.sum() == 5000
    assert abs(np.trace(conf) / 5000 - disp["test_accuracy"]) < 1e-9
    assert len(disp["per_class_accuracy"]) == 10
    assert 0 < disp["train_accuracy"] <= 1
    assert len(disp["mistakes"]) == 12
    m = disp["mistakes"][0]
    assert m["true"] != m["pred"] and len(m["pixels"]) == 784 and 0 <= m["confidence"] <= 1
    # mistakes are ordered by confidence, most confident first
    confs = [x["confidence"] for x in disp["mistakes"]]
    assert confs == sorted(confs, reverse=True)

    perfect = viz.submission_display(_good_predictions(mnist), mnist)
    assert perfect["mistakes"] == [] and perfect["test_accuracy"] == 1.0


def test_challenge_api(client):
    detail = client.get("/api/challenges/mnist_small").json()
    assert detail["evaluator"] == "multiclass_classification"
    assert detail["visualization"] == "generalization_arena"
    assert [t["id"] for t in detail["submission_types"]] == ["python_bundle"]
    assert {r["name"] for r in detail["resources"]} == {"mnist_train.csv", "submission_template.py"}
    r = client.get("/api/challenges/mnist_small/resources/mnist_train.csv")
    assert r.status_code == 200 and r.text.startswith("id,label,p0,")
    display = client.get("/api/challenges/mnist_small/display").json()
    assert display["visualization"] == "generalization_arena"
    assert display["data"]["image_shape"] == [28, 28]
