import io

import numpy as np

from app.worker import run_once
from tests.conftest import TEACHER, make_csv


def _csv_bytes(moons_ctx, good=True):
    if good:
        X_test = moons_ctx.inputs["test"].X
        G = moons_ctx.inputs["grid"].X
        f = lambda X: 1 / (1 + np.exp(2.5 * X[:, 1] - 0.5 * X[:, 0] + 0.3))  # noqa: E731
        return make_csv(moons_ctx, {"test": f(X_test), "grid": f(G)}).encode()
    return make_csv(moons_ctx).replace("test,0,0.5", "test,0,7", 1).encode()


def test_health_and_challenges(client):
    assert client.get("/api/health").json()["status"] == "ok"
    ch = client.get("/api/challenges").json()
    assert any(c["id"] == "moons" for c in ch)
    detail = client.get("/api/challenges/moons").json()
    assert "instructions_md" in detail and len(detail["resources"]) >= 3
    assert {t["id"] for t in detail["submission_types"]} == {"prediction_csv", "python_bundle"}


def test_resources_download_and_hidden_labels_not_exposed(client):
    r = client.get("/api/challenges/moons/resources/test_features.csv")
    assert r.status_code == 200 and r.text.startswith("id,x1,x2\n")
    assert "label" not in r.text.splitlines()[0]
    for name in ("test_labels.csv", "labels.csv", "y_test.csv", "../data.py"):
        assert client.get(f"/api/challenges/moons/resources/{name}").status_code == 404
    train = client.get("/api/challenges/moons/resources/train.csv").text
    assert train.startswith("id,x1,x2,label\n")
    display = client.get("/api/challenges/moons/display").json()
    assert display["visualization"] == "decision_boundary_arena"
    assert len(display["data"]["points"]["x"]) == 600


def test_teacher_auth_required(client):
    assert client.post("/api/teacher/sessions", json={"challenge_id": "moons"}).status_code == 401
    assert (
        client.post(
            "/api/teacher/sessions",
            json={"challenge_id": "moons"},
            headers={"X-Teacher-Secret": "nope"},
        ).status_code
        == 401
    )
    assert client.get("/api/teacher/verify", headers=TEACHER).status_code == 200


def test_join_and_submit_flow(client, make_session, join, moons_ctx):
    session = make_session(name="Flow")
    assert client.get(f"/api/sessions/by-code/{session['join_code'].lower()}").status_code == 200
    joined = join(session, "Mia")
    token = {"X-Participant-Token": joined["token"]}

    # unknown code
    assert (
        client.post(
            "/api/sessions/join", json={"join_code": "ZZZZZZ", "display_name": "x"}
        ).status_code
        == 404
    )
    # no token
    assert client.get("/api/sessions/me").status_code == 401
    me = client.get("/api/sessions/me", headers=token).json()
    assert me["participant"]["display_name"] == "Mia" and me["submissions"] == []

    # wrong file type
    r = client.post(
        f"/api/sessions/{session['id']}/submissions",
        headers=token,
        files={"file": ("x.txt", b"hi")},
    )
    assert r.status_code == 422

    r = client.post(
        f"/api/sessions/{session['id']}/submissions",
        headers=token,
        files={"file": ("preds.csv", _csv_bytes(moons_ctx), "text/csv")},
    )
    assert r.status_code == 202, r.text
    sub = r.json()
    assert sub["status"] == "queued" and sub["submission_type"] == "prediction_csv"

    # a second one while pending -> 429
    r = client.post(
        f"/api/sessions/{session['id']}/submissions",
        headers=token,
        files={"file": ("preds.csv", _csv_bytes(moons_ctx), "text/csv")},
    )
    assert r.status_code == 429

    assert run_once("test-worker") is True
    assert run_once("test-worker") is False

    got = client.get(f"/api/submissions/{sub['id']}").json()
    assert got["status"] == "succeeded"
    assert 0.8 < got["primary_score"] < 1.0
    assert set(got["metrics"]) >= {"accuracy", "log_loss", "brier", "n_predictions", "submitted_at"}
    disp = client.get(f"/api/submissions/{sub['id']}/display").json()
    assert len(disp["data"]["grid_probabilities"]) == 10000

    live = client.get(f"/api/sessions/{session['id']}/live").json()
    p = live["participants"][0]
    assert p["best_submission_id"] == sub["id"] and p["rank"] == 1 and p["n_submissions"] == 1

    me = client.get("/api/sessions/me", headers=token).json()
    assert me["participant"]["rank"] == 1 and me["submissions"][0]["status"] == "succeeded"


def test_invalid_submission_fails_cleanly(client, make_session, join, moons_ctx):
    session = make_session()
    token = {"X-Participant-Token": join(session, "Leo")["token"]}
    r = client.post(
        f"/api/sessions/{session['id']}/submissions",
        headers=token,
        files={"file": ("bad.csv", _csv_bytes(moons_ctx, good=False), "text/csv")},
    )
    assert r.status_code == 202
    run_once("w")
    got = client.get(f"/api/submissions/{r.json()['id']}").json()
    assert got["status"] == "failed"
    assert "validation" in got["error_message"]
    assert any("outside [0, 1]" in d for d in got["error_details"])
    failures = client.get(f"/api/teacher/sessions/{session['id']}/failures", headers=TEACHER).json()
    assert failures and failures[0]["id"] == got["id"]
    assert client.get("/api/health").status_code == 200


def test_oversized_upload_rejected(client, make_session, join, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 1000)
    session = make_session()
    token = {"X-Participant-Token": join(session, "Sam")["token"]}
    big = b"dataset,id,probability\n" + b"test,0,0.5\n" * 500
    r = client.post(
        f"/api/sessions/{session['id']}/submissions",
        headers=token,
        files={"file": ("big.csv", big, "text/csv")},
    )
    assert r.status_code == 413
    assert client.get("/api/sessions/me", headers=token).json()["submissions"] == []


def test_malicious_zip_fails_cleanly(client, make_session, join):
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../etc/cron.d/evil", "x")
        zf.writestr("submission.py", "def predict(X): return X[:,0]")
    session = make_session()
    token = {"X-Participant-Token": join(session, "Eve")["token"]}
    r = client.post(
        f"/api/sessions/{session['id']}/submissions",
        headers=token,
        files={"file": ("submission.zip", buf.getvalue(), "application/zip")},
    )
    assert r.status_code == 202 and r.json()["submission_type"] == "python_bundle"
    run_once("w")
    got = client.get(f"/api/submissions/{r.json()['id']}").json()
    assert got["status"] == "failed" and "traversal" in got["error_message"]


def test_session_controls_and_events(client, make_session, join, moons_ctx):
    session = make_session()
    sid = session["id"]
    token = {"X-Participant-Token": join(session, "Priya")["token"]}

    r = client.patch(
        f"/api/teacher/sessions/{sid}", json={"accepting_submissions": False}, headers=TEACHER
    )
    assert r.json()["accepting_submissions"] is False
    r = client.post(
        f"/api/sessions/{sid}/submissions",
        headers=token,
        files={"file": ("p.csv", _csv_bytes(moons_ctx), "text/csv")},
    )
    assert r.status_code == 409
    client.patch(
        f"/api/teacher/sessions/{sid}",
        json={"accepting_submissions": True, "scores_hidden": True},
        headers=TEACHER,
    )
    r = client.post(
        f"/api/sessions/{sid}/submissions",
        headers=token,
        files={"file": ("p.csv", _csv_bytes(moons_ctx), "text/csv")},
    )
    assert r.status_code == 202
    run_once("w")
    me = client.get("/api/sessions/me", headers=token).json()
    assert me["scores_hidden"] is True and me["participant"]["best_score"] is None
    assert me["submissions"][0]["primary_score"] is None
    teacher_view = client.get(
        f"/api/submissions/{me['submissions'][0]['id']}", headers=TEACHER
    ).json()
    assert teacher_view["primary_score"] is not None

    # Event log: replay from the beginning.
    # (The test client buffers responses, so use once=true to fetch the backlog and close.)
    resp = client.get(f"/api/sessions/{sid}/events?after=0&once=true")
    assert resp.status_code == 200 and resp.headers["content-type"].startswith("text/event-stream")
    text = resp.text
    assert "event: participant_joined" in text and "event: session_updated" in text
    assert "submission_updated" in text and '"status":"succeeded"' in text
    ids = [int(line[4:]) for line in text.splitlines() if line.startswith("id: ")]
    assert ids == sorted(ids) and len(ids) >= 4
    # Resume after the last id -> nothing new.
    resp = client.get(
        f"/api/sessions/{sid}/events?once=true", headers={"Last-Event-ID": str(ids[-1])}
    )
    assert "event:" not in resp.text

    sessions = client.get("/api/teacher/sessions", headers=TEACHER).json()
    mine = next(s for s in sessions if s["id"] == sid)
    assert mine["n_participants"] == 1 and mine["n_submissions"] == 1

    assert client.post(f"/api/teacher/sessions/{sid}/reset", headers=TEACHER).status_code == 200
    assert client.get(f"/api/sessions/{sid}/live").json()["participants"] == []
    assert client.get("/api/sessions/me", headers=token).status_code == 401
    assert client.delete(f"/api/teacher/sessions/{sid}", headers=TEACHER).status_code == 200
    assert client.get(f"/api/sessions/{sid}").status_code == 404


def test_teacher_can_toggle_submission_types(client, make_session, join, moons_ctx):
    session = make_session()
    sid = session["id"]
    assert session["enabled_submission_types"] == ["prediction_csv", "python_bundle"]
    token = {"X-Participant-Token": join(session, "Kai")["token"]}

    # Disable CSV: a CSV upload is refused with an explanatory message, ZIP still accepted.
    r = client.patch(
        f"/api/teacher/sessions/{sid}",
        json={"enabled_submission_types": ["python_bundle"]},
        headers=TEACHER,
    )
    assert r.status_code == 200 and r.json()["enabled_submission_types"] == ["python_bundle"]
    r = client.post(
        f"/api/sessions/{sid}/submissions",
        headers=token,
        files={"file": ("p.csv", _csv_bytes(moons_ctx), "text/csv")},
    )
    assert r.status_code == 422 and "disabled by the teacher" in r.json()["detail"]
    assert client.get("/api/sessions/me", headers=token).json()["session"][
        "enabled_submission_types"
    ] == ["python_bundle"]

    # Validation of the patch itself.
    assert (
        client.patch(
            f"/api/teacher/sessions/{sid}", json={"enabled_submission_types": []}, headers=TEACHER
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/teacher/sessions/{sid}",
            json={"enabled_submission_types": ["onnx"]},
            headers=TEACHER,
        ).status_code
        == 422
    )

    # Re-enable CSV -> upload works; the change was broadcast as a session_updated event.
    client.patch(
        f"/api/teacher/sessions/{sid}",
        json={"enabled_submission_types": ["prediction_csv", "python_bundle"]},
        headers=TEACHER,
    )
    r = client.post(
        f"/api/sessions/{sid}/submissions",
        headers=token,
        files={"file": ("p.csv", _csv_bytes(moons_ctx), "text/csv")},
    )
    assert r.status_code == 202
    assert run_once("w") is True  # drain the queue so later tests start clean
    events = client.get(f"/api/sessions/{sid}/events?after=0&once=true").text
    assert '"enabled_submission_types":["python_bundle"]' in events
    live = client.get(f"/api/sessions/{sid}/live").json()
    assert [t["id"] for t in live["challenge"]["submission_types"]] == [
        "prediction_csv",
        "python_bundle",
    ]
