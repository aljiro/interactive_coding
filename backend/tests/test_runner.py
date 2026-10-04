"""Sandbox tests: require Docker and the built runner image (``make runner``)."""

from __future__ import annotations

import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

import pytest

from app.core import SubmissionError, SubmissionTimeout, adapters, evaluators
from app.core.submission_adapter import AdapterContext

pytestmark = pytest.mark.docker


def _docker_ready(image: str) -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        r = subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=20)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


@pytest.fixture(scope="module", autouse=True)
def _require_docker(request):
    from app.config import get_settings

    if not _docker_ready(get_settings().runner_image):
        pytest.skip("Docker or the runner image is not available (run `make runner`)")


def _bundle(tmp_path: Path, code: str, extra: dict[str, bytes] | None = None) -> Path:
    z = tmp_path / "submission.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("submission.py", code)
        for name, data in (extra or {}).items():
            zf.writestr(name, data)
    return z


@pytest.fixture
def ctx(moons, settings) -> AdapterContext:
    """Work dirs live under DATA_DIR so the sandbox can mount them in both bind and volume mode."""
    settings.runner_timeout_seconds = 20
    workdir = Path(settings.data_dir) / "test-jobs" / uuid.uuid4().hex
    workdir.mkdir(parents=True)
    yield AdapterContext(challenge=moons, inputs=moons.inputs(), workdir=workdir, settings=settings)
    shutil.rmtree(workdir, ignore_errors=True)


def _run(ctx, zip_path):
    return adapters.get("python_bundle").run(zip_path, ctx)


def test_minimal_torch_submission_succeeds(ctx, moons, tmp_path):
    code = """
import os, numpy as np, torch
here = os.path.dirname(os.path.abspath(__file__))
w = np.load(os.path.join(here, "weights.npy"))
lin = torch.nn.Linear(2, 1)
with torch.no_grad():
    lin.weight[:] = torch.tensor(w[:2]).reshape(1, 2); lin.bias[:] = float(w[2])
def predict(X):
    with torch.no_grad():
        return torch.sigmoid(lin(torch.tensor(X, dtype=torch.float32))).numpy().ravel()
"""
    import io

    import numpy as np

    buf = io.BytesIO()
    np.save(buf, np.array([0.5, -2.5, -0.3], dtype=np.float32))
    preds = _run(ctx, _bundle(tmp_path, code, {"weights.npy": buf.getvalue()}))
    assert preds["test"].shape == (1000,) and preds["grid"].shape == (10000,)
    out = evaluators.get(moons.evaluator).evaluate(
        preds, moons.hidden_targets(), moons.evaluator_config
    )
    assert 0.8 < out.primary_score < 1.0
    assert preds.info["runtime_seconds"] < 20


def test_syntax_error_reported(ctx, tmp_path):
    with pytest.raises(SubmissionError) as exc:
        _run(ctx, _bundle(tmp_path, "def predict(X)\n    return X"))
    assert "SyntaxError" in exc.value.message
    assert exc.value.status == "failed"


def test_runtime_error_reported(ctx, tmp_path):
    with pytest.raises(SubmissionError) as exc:
        _run(ctx, _bundle(tmp_path, "def predict(X):\n    return X[:, 7]"))
    assert "IndexError" in exc.value.message
    assert any("submission.py" in d for d in exc.value.details)


def test_wrong_shape_reported(ctx, tmp_path):
    with pytest.raises(SubmissionError, match="expected"):
        _run(ctx, _bundle(tmp_path, "def predict(X):\n    return X[:5, 0]"))


def test_infinite_loop_is_terminated(ctx, tmp_path, settings):
    settings.runner_timeout_seconds = 4
    with pytest.raises(SubmissionTimeout) as exc:
        _run(ctx, _bundle(tmp_path, "def predict(X):\n    while True:\n        pass"))
    assert exc.value.status == "timed_out"
    names = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output=True, text=True
    ).stdout
    assert "arena-run-" not in names, "container was not cleaned up"


def test_no_network_access(ctx, tmp_path):
    code = """
import socket, numpy as np
def predict(X):
    reachable = 0.0
    for host, port in (("1.1.1.1", 53), ("8.8.8.8", 443)):
        try:
            socket.create_connection((host, port), timeout=2).close()
            reachable = 1.0
        except OSError:
            pass
    try:
        socket.gethostbyname("example.com"); reachable = 1.0
    except OSError:
        pass
    return np.full(len(X), reachable)
"""
    preds = _run(ctx, _bundle(tmp_path, code))
    assert preds["test"].max() == 0.0


def test_hidden_labels_not_available(ctx, tmp_path):
    code = """
import os, numpy as np
SUSPICIOUS = ("label", "target", "y_test", "hidden", ".csv", ".db", "docker.sock", "secret")
def predict(X):
    found = []
    for root in ("/inputs", "/bundle", "/data", "/app", "/home", "/root", "/mnt", "/srv", "/var/run", "/run", "/"):
        if not os.path.isdir(root):
            continue
        depth0 = root.rstrip("/").count("/")
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath.count("/") - depth0 >= (1 if root == "/" else 6):
                dirnames[:] = []
            if dirpath.startswith(("/proc", "/sys", "/dev", "/usr", "/lib", "/etc", "/bin", "/sbin", "/opt")):
                dirnames[:] = []
                continue
            for f in filenames:
                if any(s in f.lower() for s in SUSPICIOUS):
                    found.append(os.path.join(dirpath, f))
    env_hits = [k for k in os.environ if any(s in k.lower() for s in ("secret", "label", "database", "teacher"))]
    inputs = sorted(os.listdir("/inputs"))
    ok = inputs == ["grid.npy", "manifest.json", "test.npy"] and not found and not env_hits
    print("found", found, "env", env_hits, "inputs", inputs)
    return np.full(len(X), 0.0 if ok else 1.0)
"""
    preds = _run(ctx, _bundle(tmp_path, code))
    assert preds["test"].max() == 0.0, preds.info.get("stderr_tail")


def test_filesystem_is_read_only_except_tmp(ctx, tmp_path):
    code = """
import os, numpy as np
def predict(X):
    bad = 0.0
    for p in ("/bundle/x", "/inputs/x", "/usr/x", "/opt/runner/x", "/x"):
        try:
            open(p, "w").write("x"); bad = 1.0
        except OSError:
            pass
    open("/tmp/ok", "w").write("x")  # must work
    return np.full(len(X), bad)
"""
    preds = _run(ctx, _bundle(tmp_path, code))
    assert preds["test"].max() == 0.0


def test_runs_as_non_root(ctx, tmp_path):
    preds = _run(
        ctx,
        _bundle(
            tmp_path,
            "import os, numpy as np\ndef predict(X):\n    return np.full(len(X), 1.0 if os.getuid() == 0 else 0.0)",
        ),
    )
    assert preds["test"].max() == 0.0
