import numpy as np
from sklearn.metrics import accuracy_score, log_loss

from app.core import PredictionSet, evaluators


def test_known_predictions_match_sklearn():
    rng = np.random.default_rng(42)
    y = rng.integers(0, 2, size=500)
    p = np.clip(y * 0.7 + rng.normal(0, 0.25, size=500), 0, 1)
    ev = evaluators.get("binary_classification")
    out = ev.evaluate(PredictionSet({"test": p}), {"test": y}, {"dataset": "test"})
    assert out.primary_score == out.metrics["accuracy"]
    assert abs(out.metrics["accuracy"] - accuracy_score(y, (p >= 0.5).astype(int))) < 1e-9
    assert abs(out.metrics["log_loss"] - log_loss(y, np.clip(p, 1e-7, 1 - 1e-7))) < 1e-5


def test_perfect_and_inverted():
    y = np.array([0, 1, 1, 0, 1])
    ev = evaluators.get("binary_classification")
    perfect = ev.evaluate(PredictionSet({"test": y.astype(float)}), {"test": y}, {})
    assert perfect.primary_score == 1.0 and perfect.metrics["log_loss"] < 1e-5
    inverted = ev.evaluate(PredictionSet({"test": 1.0 - y}), {"test": y}, {})
    assert inverted.primary_score == 0.0


def test_moons_pipeline_on_real_data(moons):
    """A simple hand-made rule should score well above chance on the hidden set."""
    X = moons.inputs()["test"].X
    p = 1 / (1 + np.exp(2.5 * X[:, 1] - 0.5 * X[:, 0] + 0.3))
    ev = evaluators.get(moons.evaluator)
    out = ev.evaluate(PredictionSet({"test": p}), moons.hidden_targets(), moons.evaluator_config)
    assert 0.8 < out.primary_score < 1.0
