"""Test fixtures. Tests run against SQLite by default (set TEST_DATABASE_URL for Postgres)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="arena-test-"))
os.environ.setdefault("TEST_DATABASE_URL", f"sqlite:///{_TMP / 'test.db'}")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ.setdefault("DATA_DIR", str(_TMP / "data"))
os.environ["TEACHER_SECRET"] = "test-secret"
os.environ["SUBMISSION_MIN_INTERVAL_SECONDS"] = "0"
os.environ["SSE_POLL_INTERVAL_SECONDS"] = "0.05"

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.core import AdapterContext, challenges  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.plugins import load_builtin  # noqa: E402

TEACHER = {"X-Teacher-Secret": "test-secret"}


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    load_builtin()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def moons():
    return challenges.get("moons")


@pytest.fixture
def moons_ctx(moons, settings, tmp_path) -> AdapterContext:
    return AdapterContext(
        challenge=moons, inputs=moons.inputs(), workdir=tmp_path, settings=settings
    )


def make_csv(
    ctx: AdapterContext,
    probs: dict[str, np.ndarray] | None = None,
    *,
    header="dataset,id,probability",
) -> str:
    lines = [header]
    for name, ds in ctx.inputs.items():
        p = probs[name] if probs else np.full(ds.n, 0.5)
        for i, v in zip(ds.ids, p, strict=True):
            lines.append(f"{name},{int(i)},{v}")
    return "\n".join(lines) + "\n"


@pytest.fixture
def make_session(client):
    def _make(challenge_id="moons", name="Test session", join_code=None):
        payload = {"challenge_id": challenge_id, "name": name}
        if join_code:
            payload["join_code"] = join_code
        r = client.post("/api/teacher/sessions", json=payload, headers=TEACHER)
        assert r.status_code == 201, r.text
        return r.json()

    return _make


@pytest.fixture
def join(client):
    def _join(session, name="Student"):
        r = client.post(
            "/api/sessions/join", json={"join_code": session["join_code"], "display_name": name}
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _join
