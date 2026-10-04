"""Proves the framework is generic: a different adapter / evaluator / visualization triple is
registered here, in a test, without touching any platform code."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.core import (
    AdapterContext,
    Challenge,
    EvaluationOutput,
    Evaluator,
    InputDataset,
    MetricSpec,
    PredictionSet,
    SubmissionAdapter,
    SubmissionError,
    VisualizationType,
    adapters,
    challenges,
    evaluators,
    visualizations,
)
from app.core.registries import register_challenge
from app.worker import run_once
from tests.conftest import TEACHER


class JsonNumberAdapter(SubmissionAdapter):
    id = "json_number"
    label = "JSON guess"
    accepted_extensions = (".json",)

    def run(self, artifact: Path, ctx: AdapterContext) -> PredictionSet:
        try:
            value = float(json.loads(artifact.read_text())["guess"])
        except Exception as exc:  # noqa: BLE001
            raise SubmissionError(
                'Expected a JSON object like {"guess": 3.14}', [str(exc)]
            ) from None
        return PredictionSet({"guess": np.array([value])})


class AbsErrorEvaluator(Evaluator):
    id = "abs_error"

    def evaluate(self, predictions, targets, config):
        err = float(abs(predictions["guess"][0] - targets["guess"][0]))
        return EvaluationOutput(primary_score=err, metrics={"abs_error": err})


class NumberLineViz(VisualizationType):
    id = "number_line"

    def submission_display(self, predictions, challenge):
        return {"guess": float(predictions["guess"][0])}


DUMMY = Challenge(
    id="dummy_guess",
    title="Guess the number",
    short_description="Lower error is better.",
    instructions_md='Upload {"guess": x}.',
    submission_type="json_number",
    evaluator="abs_error",
    visualization="number_line",
    primary_metric=MetricSpec("abs_error", "absolute error", higher_is_better=False),
    inputs=lambda: {"guess": InputDataset("guess", np.array([0]), np.zeros((1, 1)))},
    hidden_targets=lambda: {"guess": np.array([42.0])},
    display_data=lambda: {"range": [0, 100]},
)


@pytest.fixture
def dummy_registered():
    adapters.register(JsonNumberAdapter(), replace=True)
    evaluators.register(AbsErrorEvaluator(), replace=True)
    visualizations.register(NumberLineViz(), replace=True)
    register_challenge(DUMMY, replace=True)
    yield
    challenges.unregister(DUMMY.id)
    adapters.unregister(JsonNumberAdapter.id)
    evaluators.unregister(AbsErrorEvaluator.id)
    visualizations.unregister(NumberLineViz.id)


def test_unknown_component_rejected():
    bad = Challenge(**{**DUMMY.__dict__, "id": "bad", "evaluator": "does_not_exist"})
    with pytest.raises(LookupError):
        register_challenge(bad)


def test_dummy_challenge_end_to_end(client, dummy_registered, make_session, join):
    assert any(c["id"] == "dummy_guess" for c in client.get("/api/challenges").json())
    session = make_session(challenge_id="dummy_guess", name="Dummy")
    alice = {"X-Participant-Token": join(session, "Alice")["token"]}
    bob = {"X-Participant-Token": join(session, "Bob")["token"]}
    for who, guess in ((alice, 40), (bob, 50)):
        r = client.post(
            f"/api/sessions/{session['id']}/submissions",
            headers=who,
            files={"file": ("g.json", json.dumps({"guess": guess}).encode(), "application/json")},
        )
        assert r.status_code == 202, r.text
        run_once("w")
    live = client.get(f"/api/sessions/{session['id']}/live").json()
    assert live["challenge"]["visualization"] == "number_line"
    by_name = {p["display_name"]: p for p in live["participants"]}
    assert by_name["Alice"]["best_score"] == 2.0 and by_name["Bob"]["best_score"] == 8.0
    assert by_name["Alice"]["rank"] == 1 and by_name["Bob"]["rank"] == 2  # lower is better
    disp = client.get(f"/api/submissions/{by_name['Bob']['best_submission_id']}/display").json()
    assert disp == {
        "submission_id": by_name["Bob"]["best_submission_id"],
        "participant_id": by_name["Bob"]["id"],
        "visualization": "number_line",
        "data": {"guess": 50.0},
    }
    assert client.get("/api/challenges/dummy_guess/display").json()["data"] == {"range": [0, 100]}

    # invalid artifact -> clean failure with the adapter's message
    r = client.post(
        f"/api/sessions/{session['id']}/submissions",
        headers=alice,
        files={"file": ("g.json", b"not json", "application/json")},
    )
    run_once("w")
    assert client.get(f"/api/submissions/{r.json()['id']}").json()["status"] == "failed"
    client.delete(f"/api/teacher/sessions/{session['id']}", headers=TEACHER)
