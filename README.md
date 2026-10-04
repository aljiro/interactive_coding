# DNNLS Live Arena

A lightweight, modular **classroom evaluation and visualization layer** for synchronous
machine-learning teaching. Students train models in Google Colab, upload a small artifact to a
shared web app, the server scores it against hidden labels, and a projector view updates live
and shows each student's solution.

The first complete challenge is **Two Moons — Decision Boundary Challenge**. The architecture
keeps submission handling, evaluation and visualization as independent, swappable modules so
very different challenges can be added without rewriting the platform.

> **Intended environment.** This MVP is designed for a *trusted university cohort on a
> classroom LAN or a university VM*. Python bundles run in a locked-down disposable Docker
> container (no network, non-root, read-only, CPU/RAM/PID/time limits), which is a strong
> defence against accidents and curious students, but it is **not advertised as an
> internet-grade hostile-code execution service**. Do not expose it to the public internet
> without additional hardening (TLS, authentication, a dedicated VM, gVisor/Kata, ...).

---

## Contents

1. [How it works](#1-how-it-works)
2. [Install on Linux (Ubuntu/Debian)](#2-install-on-linux-ubuntudebian)
3. [Install on Windows 10/11](#3-install-on-windows-1011)
4. [Running a class](#4-running-a-class)
5. [Architecture](#5-architecture)
6. [Isolated execution of Python submissions](#6-isolated-execution-of-python-submissions)
7. [API](#7-api)
8. [Adding a new challenge](#8-adding-a-new-challenge)
9. [Development](#9-development)
10. [Testing](#10-testing)
11. [Configuration reference](#11-configuration-reference)
12. [Security notes](#12-security-notes)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. How it works

```
Student trains in Colab
        ↓
submission artifact            prediction CSV  -or-  submission.zip (submission.py + weights.pt)
        ↓
SubmissionAdapter              validates the artifact (columns, ids, ranges, ZIP safety, ...)
        ↓
optional isolated model runner disposable Docker container calls predict(X) on public inputs
        ↓
predictions                    one array per public input dataset (e.g. "test", "grid")
        ↓
Evaluator + hidden labels      primary score + secondary metrics (accuracy, log loss, ...)
        ↓
structured result              {"primary_score": 0.971, "metrics": {...}} + display payload
        ↓
database                       PostgreSQL (submissions, results, job queue, event log)
        ↓
SSE live update                /api/sessions/{id}/events pushes changes to open browsers
        ↓
challenge Visualization        React plugin (e.g. decision boundary + score blobs)
```

The three middle concerns — **submission adapter**, **evaluator**, **visualization** — are
independent modules referenced by stable ids from a declarative challenge definition:

```python
Challenge(
    id="moons",
    submission_type="python_bundle",        # SubmissionAdapter id (CSV also allowed, see adapter_config)
    evaluator="binary_classification",      # Evaluator id
    visualization="decision_boundary_arena",# VisualizationType id (backend + frontend plugin)
    ...
)
```

Nothing in the generic session / submission / leaderboard / live-update code knows anything
about moons, probabilities or decision boundaries.

---

## 2. Install on Linux (Ubuntu/Debian)

Docker is the only dependency. You do **not** need Python, Node or PostgreSQL on the machine.

### 2.1 Install Docker Engine + the Compose plugin

```bash
# Official Docker repository (see https://docs.docker.com/engine/install/ubuntu/ for details)
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Let your user run docker without sudo (log out and back in afterwards)
sudo usermod -aG docker $USER
```

On Debian replace `ubuntu` with `debian` in the two URLs. Docker Engine **25 or newer** is
required (the worker mounts sub-paths of a named volume into the sandbox).

### 2.2 Verify

```bash
docker --version
docker compose version
```

### 2.3 Get the repository

```bash
git clone <this repository> dnnls-arena
cd dnnls-arena
```

### 2.4 Configure

```bash
cp .env.example .env
nano .env        # at least change TEACHER_SECRET
```

### 2.5 Start

```bash
docker compose up -d --build
```

The first build downloads the base images and the sandbox stack (numpy/scipy/scikit-learn/
PyTorch CPU ≈ 1.5 GB) and takes several minutes. Later starts are fast.

### 2.6 Open

```
http://localhost:8000
```

* `/` — student join page
* `/teacher` — teacher controls (enter `TEACHER_SECRET`)
* `/live/<session id>` — projector view (opened from the teacher page)
* `/api/docs` — interactive API documentation

### 2.7 Classroom LAN access

The app binds to `0.0.0.0`, so other devices on the same network can reach it. Find your IP:

```bash
hostname -I          # e.g. 192.168.1.23 10.0.0.5 ...
```

Students browse to `http://<TEACHER-LAN-IP>:8000`, e.g. `http://192.168.1.23:8000`.

If a firewall is active, allow the port (UFW example):

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

Test from a second device (phone/laptop on the same Wi-Fi) before the lecture. Some
university Wi-Fi networks use **client isolation**, which blocks device-to-device traffic even
when everything is configured correctly; see [Troubleshooting](#13-troubleshooting).

### 2.8 Stop / update / logs

```bash
docker compose logs -f            # follow logs (Ctrl-C to stop following)
docker compose down               # stop (data is kept in Docker volumes)
git pull                          # get a new version
docker compose pull               # refresh base images (postgres etc.)
docker compose up -d --build      # rebuild and restart
docker compose down -v            # stop AND delete all data (sessions, submissions)
```

---

## 3. Install on Windows 10/11

Use **Docker Desktop with the WSL 2 backend and Linux containers**.

1. **Enable WSL 2** (skip if already installed). In an *administrator* PowerShell:
   ```powershell
   wsl --install
   ```
   Reboot when asked. (`wsl --status` shows whether WSL 2 is the default.)
2. **Install Docker Desktop** from <https://www.docker.com/products/docker-desktop/>
   and start it. Accept the WSL 2 integration prompt.
3. **Check the backend**: Docker Desktop → *Settings → General* → "Use the WSL 2 based engine"
   must be ticked, and the whale menu must say *Switch to Windows containers...* (meaning
   Linux containers are active). Under *Settings → Resources* give Docker at least 4 GB RAM.
4. **Verify** in PowerShell:
   ```powershell
   docker --version
   docker compose version
   ```
5. **Get the repository** (Git for Windows, GitHub Desktop, or download + unzip):
   ```powershell
   git clone <this repository> dnnls-arena
   cd dnnls-arena
   ```
6. **Configure**:
   ```powershell
   Copy-Item .env.example .env
   notepad .env        # change TEACHER_SECRET
   ```
7. **Start**:
   ```powershell
   docker compose up -d --build
   ```
   (`.\scripts\arena.ps1 up` does the same; see `.\scripts\arena.ps1 help`.)
8. **Browse** to `http://localhost:8000`.

### 3.1 Classroom LAN access on Windows

Find the IPv4 address of the active adapter:

```powershell
ipconfig
```

Look for the adapter you are connected with (e.g. *Wireless LAN adapter Wi-Fi*) and its
**IPv4 Address**, e.g. `192.168.1.42`. Students browse to:

```
http://<WINDOWS-IP>:8000
```

**Windows Defender Firewall** usually blocks inbound connections from other devices. Add an
inbound rule for TCP port 8000 (administrator PowerShell):

```powershell
New-NetFirewallRule -DisplayName "DNNLS Live Arena" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

Alternatively *Windows Security → Firewall & network protection → Advanced settings → Inbound
Rules → New Rule → Port → TCP 8000 → Allow*. Make sure the network is marked *Private* if the
rule is limited to private profiles.

### 3.2 Test with a second device — and client isolation

Before class, open `http://<WINDOWS-IP>:8000` on a **second device** (phone or another laptop)
connected to the **same** network. If the page loads, students will be able to connect.

If it does *not* load although `http://localhost:8000` works on the teacher laptop and the
firewall rule exists, the network most likely uses **client isolation** (common on eduroam and
guest Wi-Fi): the access point deliberately blocks traffic between client devices. This is
institutional network security and **this project does not attempt to work around it**. Options:

* use a different network (a dedicated lab network, a wired connection, a travel router or a
  phone hotspot for small groups), or
* deploy exactly the same `docker compose` application on a **university Linux VM** with a
  reachable hostname; students then use `http://<vm-hostname>:8000`. Nothing in the setup
  changes except where `docker compose up -d --build` is run.

### 3.3 Stop / update / logs (PowerShell)

```powershell
docker compose logs -f
docker compose down
docker compose pull
docker compose up -d --build
```

---

## 4. Running a class

1. Open `http://localhost:8000/teacher`, enter the teacher secret.
2. **Create a session**: pick the challenge, give it a name (optionally a custom join code).
   A 6-character join code is generated.
3. Click **Open projector view** and put it on the beamer. The header shows the address
   and join code students need. Open the teacher page via the LAN address
   (`http://<TEACHER-IP>:8000/teacher`) so that the projector header shows an address students
   can actually type, not `localhost`.
4. Students open `http://<TEACHER-IP>:8000`, enter the code and a display name. They appear
   immediately on the projector in the "no evaluated submission yet" row.
5. Students work in Colab (`examples/moons_colab.ipynb`, also downloadable from the student
   page). The notebook fetches the public data from `examples/data/` on GitHub, because Colab
   cannot reach a server on the classroom LAN. Students download their `predictions.csv` or
   `submission.zip` and upload it on their student page. Their blob moves to its score within a second or two (ZIP bundles take a few seconds
   longer because a sandbox container starts).
6. Click any blob (or a row of the table) to show that student's decision boundary. With
   **follow latest** ticked, the projector automatically switches to each new evaluated
   submission.
7. Teacher controls: **stop/start accepting submissions**, **hide scores** (blobs still move,
   numbers and ranks disappear), **per-type toggles** (e.g. allow only prediction CSVs, or only
   Python bundles; at least one type stays enabled), **show failures** (validation errors / sandbox errors),
   **reset** (removes participants and submissions, keeps the code) and **delete**.

### Demo mode

To see the projector view without students:

```bash
docker compose exec web python -m app.scripts.seed_demo        # or: make demo
```

creates a session with join code **DEMO**, 13 fake participants, 12 real decision surfaces
from classic classifiers (logistic regression, kNN, SVM, random forest, MLP, ...), one failed
submission and one student who has not submitted yet. The command prints the projector URL.
Re-running it recreates the demo session.

### Ranking / selection rule

* A participant's **best submission** is their *succeeded* submission with the best primary
  score (ties → the earlier one). Blob position and leaderboard rank use the best score.
* **Clicking a blob selects the best submission.** A drop-down in the detail panel lets you
  show any other evaluated submission of that student.
* **Follow latest** (projector toggle, on by default) selects the submission that has *just*
  been evaluated, even if it is not that student's best.

---

## 5. Architecture

```
dnnls-arena/
├── backend/
│   ├── app/
│   │   ├── api/                    FastAPI routers (challenges, sessions, submissions, SSE, teacher)
│   │   ├── core/                   generic framework: Challenge, SubmissionAdapter, Evaluator,
│   │   │                           VisualizationType, registries
│   │   ├── challenges/moons/       the reference challenge (data, instructions, resources)
│   │   ├── submissions/            adapters: prediction_csv, python_bundle (+ zip_safety)
│   │   ├── evaluators/             binary_classification
│   │   ├── visualizations/         decision_boundary_arena (backend half: display payloads)
│   │   ├── runners/                DockerRunner: disposable sandbox containers
│   │   ├── models/                 SQLAlchemy entities
│   │   ├── schemas/                Pydantic API models
│   │   ├── services/               sessions, storage, job queue, evaluation pipeline, live snapshot
│   │   ├── scripts/seed_demo.py
│   │   ├── worker.py               evaluation worker process
│   │   └── main.py                 FastAPI app + static frontend
│   ├── alembic/                    migrations
│   └── tests/
├── frontend/src/
│   ├── challenge-visualizations/   plugin registry + decision-boundary-arena + fallback
│   ├── components/                 leaderboard, upload control, detail panel, ...
│   ├── pages/                      Home (join), Student, Teacher, Projector
│   └── api/                        typed client + SSE hook
├── runner-images/python-ml/        sandbox image (numpy, scipy, scikit-learn, torch) + entry script
├── examples/moons_colab.ipynb      starter notebook
├── examples/data/                  committed public Moons files (what Colab downloads)
├── docker-compose.yml  docker-compose.dev.yml  Dockerfile  Makefile  scripts/arena.ps1
└── .env.example
```

### Data model

| entity | notes |
|---|---|
| **Challenge** | *code*, not a table: a declarative `Challenge` object registered under a stable id (`app/core/challenge.py`). A session stores the id. |
| **ClassSession** | one run of a challenge with a cohort: name, join code, `accepting_submissions`, `scores_hidden`, `enabled_submission_types` (subset of the challenge's adapters, NULL = all) |
| **Participant** | generated UUID, display name, optional student identifier, SHA-256 hash of a random token (the token lives in the browser's local storage) |
| **Submission** | status (`uploaded → queued → running → succeeded / failed / timed_out`), adapter id, server-generated artifact path, sanitised original filename, error message/details |
| **EvaluationResult** | `primary_score`, `metrics` (JSON), `display_data` (JSON payload for the visualization plugin) |
| **EvaluationJob** | persistent queue record claimed with `SELECT … FOR UPDATE SKIP LOCKED` |
| **SessionEvent** | append-only per-session event log that the SSE endpoint streams |

### Services

* **web** — FastAPI (uvicorn). Serves `/api/*` and the built React app from the same origin.
  Runs Alembic migrations at start.
* **worker** — claims jobs transactionally, runs the evaluation pipeline, records
  results/failures. Can be restarted at any time; queued jobs are never lost and jobs stuck in
  `running` are re-queued after `STALE_JOB_SECONDS`.
* **db** — PostgreSQL 16.
* **runner-builder** — builds the sandbox image `dnnls-arena-runner:latest` and exits.

### Live updates

Every state change appends a `SessionEvent` row. `GET /api/sessions/{id}/events` is a
Server-Sent Events stream: each connection polls the event table (indexed, every 0.5 s), sends
new rows, and sends heartbeats. Browsers reconnect automatically and resume with
`Last-Event-ID`, so nothing is missed. Events carry enough data (updated participant
aggregate + submission) for the UI to update without reloading. A full snapshot is available at
`GET /api/sessions/{id}/live`.

### Visualization plugins

The backend `VisualizationType` decides *what public display data* to store
(`session_display(challenge)` once per challenge; `submission_display(predictions, challenge)`
per submission). The frontend plugin with the same id (`frontend/src/challenge-visualizations`)
renders it. For the Moons arena the stored per-submission payload is the 100×100 grid of class-1
probabilities; the frontend reconstructs the probability field and the 0.5 contour with
`d3-contour`, so the original model is never needed again.

The generic projector page handles data loading, selection, the compact table and the
"follow latest" behaviour; the plugin receives `participants`, `sessionDisplay`,
`selected` (submission + display payload), `recent` updates and callbacks, and is free to map
scores to *any* encoding (accuracy vs parameter count, train-vs-test, trajectories, embeddings,
...). Only the Moons plugin assumes "higher = better score"; a challenge whose metric is
lower-is-better (see the dummy challenge in the tests) still ranks correctly because
`MetricSpec.higher_is_better` is part of the challenge definition.

---

## 6. Isolated execution of Python submissions

Student Python code is **never imported in the web or worker process**. The adapter:

1. extracts the ZIP with `safe_extract_zip` — rejects absolute paths, `..`, symlinks, more than
   `ZIP_MAX_FILES` entries, more than `ZIP_MAX_UNCOMPRESSED_BYTES` (checked both from headers
   and while streaming), and suspicious compression ratios;
2. writes the public input features (`test.npy`, `grid.npy`, `manifest.json`) into a job
   directory — **the hidden labels are never written there**;
3. starts a container from the allowlisted image `dnnls-arena-runner:latest` with

| flag | purpose |
|---|---|
| `--network none` | no network access |
| `--user 1000:1000` | non-root |
| `--read-only` | read-only root filesystem |
| `--mount …,readonly` for `/bundle` and `/inputs` | student code and features read-only |
| `--tmpfs /tmp:size=256m` | the only writable location |
| `--memory 512m --memory-swap 512m` | RAM limit |
| `--cpus 1.0` | CPU limit |
| `--pids-limit 64` | process limit |
| `--cap-drop ALL --security-opt no-new-privileges` | no capabilities, no privilege escalation |
| `--rm` + `docker kill` after `RUNNER_TIMEOUT_SECONDS` | wall-clock timeout, container destroyed |

4. the entry script `run_submission.py` redirects the student's stdout to stderr, imports
   `submission.py`, calls `predict(X)` once per input dataset and prints **one JSON document**
   with the predictions. Nothing else leaves the container.

The worker reaches the Docker daemon through `/var/run/docker.sock`. Because the worker itself
runs in a container, job directories are made visible to the sandbox as **read-only sub-paths of
the named volume `dnnls_arena_data`** (`RUNNER_MOUNT_MODE=volume`, Docker ≥ 25). For local
development outside Docker, `RUNNER_MOUNT_MODE=bind` uses plain bind mounts of `DATA_DIR`.

The sandbox image contains Python 3.12 with `numpy`, `scipy`, `scikit-learn` and CPU `torch`.
Rebuild it after editing `runner-images/python-ml/`:

```bash
docker compose build runner-builder      # or: make runner
```

**Scope reminder:** this isolates *accidental* and *curious* misuse for a trusted cohort. Kernel
exploits, Docker-daemon vulnerabilities and hardware side channels are out of scope.

---

## 7. API

Interactive docs: `http://localhost:8000/api/docs` (OpenAPI at `/api/openapi.json`).

| method | path | auth | purpose |
|---|---|---|---|
| GET | `/api/health` | – | liveness |
| GET | `/api/challenges` | – | list challenges |
| GET | `/api/challenges/{id}` | – | instructions, resources, accepted submission types |
| GET | `/api/challenges/{id}/display` | – | static display data for the visualization |
| GET | `/api/challenges/{id}/resources/{name}` | – | download a public file |
| POST | `/api/sessions/join` | – | `{join_code, display_name}` → participant token |
| GET | `/api/sessions/by-code/{code}` | – | session preview |
| GET | `/api/sessions/me` | participant | my participant, submissions, rank |
| GET | `/api/sessions/{id}` | – | public session info |
| GET | `/api/sessions/{id}/live` | – | full snapshot (participants + aggregates) |
| GET | `/api/sessions/{id}/events` | – | SSE stream (`?after=`, `Last-Event-ID`, `?once=true`) |
| POST | `/api/sessions/{id}/submissions` | participant | multipart upload (`file`) → 202 |
| GET | `/api/sessions/{id}/submissions` | – | list (`?participant_id=`) |
| GET | `/api/submissions/{id}` | – | status + result |
| GET | `/api/submissions/{id}/display` | – | visualization payload |
| GET | `/api/teacher/verify` | teacher | check the secret |
| GET/POST | `/api/teacher/sessions` | teacher | list / create |
| PATCH/DELETE | `/api/teacher/sessions/{id}` | teacher | update `name`, `accepting_submissions`, `scores_hidden`, `enabled_submission_types` / delete |
| POST | `/api/teacher/sessions/{id}/reset` | teacher | remove participants and submissions |
| GET | `/api/teacher/sessions/{id}/failures` | teacher | failed submissions with details |

Auth headers: `X-Participant-Token: <token from join>` and `X-Teacher-Secret: <TEACHER_SECRET>`.

SSE event types: `participant_joined`, `submission_updated` (payload: `submission`,
`participant` aggregate with `improved` flag), `session_updated`, `session_reset`,
`session_deleted`.

---

## 8. Adding a new challenge

Minimum: **one package** under `backend/app/challenges/<id>/` exposing `CHALLENGE`. It is
discovered automatically at start-up. Reuse existing adapters/evaluators/visualizations by id;
add new ones only when needed.

### 8.0 Public data files

Public challenge files are generated in code and served by the API, and the Moons ones are
also committed under `examples/data/` so Colab can fetch them from GitHub. After changing the
data generation, regenerate them (a test fails otherwise):

```bash
docker compose exec web python -m app.scripts.export_public_data   # writes examples/data/*.csv (inside the container; copy out) 
cd backend && .venv/bin/python -m app.scripts.export_public_data    # or locally
```

Hidden labels are never exported.

### 8.1 A new challenge reusing existing components

```python
# backend/app/challenges/circles/__init__.py
import numpy as np
from sklearn.datasets import make_circles
from app.core import Challenge, InputDataset, MetricSpec, Resource

def _inputs():
    X_test, _ = make_circles(500, noise=0.1, random_state=2)
    grid = ...  # (nx*ny, 2), x fastest
    return {"test": InputDataset("test", np.arange(500), X_test),
            "grid": InputDataset("grid", np.arange(len(grid)), grid)}

def _hidden():
    _, y = make_circles(500, noise=0.1, random_state=2)
    return {"test": y}

CHALLENGE = Challenge(
    id="circles", title="Concentric circles", short_description="...", instructions_md="...",
    submission_type="prediction_csv", evaluator="binary_classification",
    visualization="decision_boundary_arena",
    primary_metric=MetricSpec("accuracy", "hidden test accuracy"),
    inputs=_inputs, hidden_targets=_hidden,
    display_data=lambda: {"points": {...}, "grid": {"nx": 100, "ny": 100, "x0": -1.5, "x1": 1.5, "y0": -1.5, "y1": 1.5},
                          "score_range": [0.5, 1.0]},
    resources=[Resource("train.csv", "training data", lambda: b"...")],
    adapter_config={"allowed_submission_types": ["prediction_csv", "python_bundle"]},
)
```

Restart `web` and `worker` — the challenge appears in the teacher's drop-down.

### 8.2 A new submission type / evaluator / visualization

Implement the interface, register it, reference it by id:

```python
# backend/app/submissions/npz_predictions.py
class NpzAdapter(SubmissionAdapter):
    id = "npz_predictions"; label = "NPZ predictions"; accepted_extensions = (".npz",)
    def run(self, artifact, ctx) -> PredictionSet:
        data = np.load(artifact)            # validate keys / shapes / ranges ...
        return PredictionSet({name: data[name] for name in ctx.inputs})

# register in backend/app/submissions/__init__.py -> register_all()
```

```python
# backend/app/evaluators/regression.py
class RegressionEvaluator(Evaluator):
    id = "regression_rmse"
    def evaluate(self, predictions, targets, config) -> EvaluationOutput:
        err = predictions["test"] - targets["test"]
        return EvaluationOutput(primary_score=float(np.sqrt((err ** 2).mean())), metrics={...})
# primary_metric=MetricSpec("rmse", "RMSE", higher_is_better=False)
```

```python
# backend/app/visualizations/accuracy_vs_params.py
class AccuracyVsParams(VisualizationType):
    id = "accuracy_vs_params"
    def submission_display(self, predictions, challenge):
        return {"n_params": predictions.info.get("n_params")}
```

```ts
// frontend/src/challenge-visualizations/accuracy-vs-params/index.tsx
export const accuracyVsParams: VisualizationPlugin = { id: 'accuracy_vs_params', Arena, SubmissionPreview };
// add it to the `plugins` map in frontend/src/challenge-visualizations/index.ts
```

`backend/tests/test_dummy_challenge.py` is a complete worked example: it registers a JSON
adapter, an absolute-error evaluator (lower is better) and a "number line" visualization, then
drives the real API end-to-end — without touching any generic code.

---

## 9. Development

### 9.1 Everything in Docker, with live reload (no local toolchain)

```bash
make dev        # = docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

* API with `--reload` on `http://localhost:8000` (backend code bind-mounted)
* worker with the code bind-mounted (restart it after edits: `docker compose restart worker`)
* Vite dev server with HMR on `http://localhost:5173` (proxies `/api` to the backend)

### 9.2 Backend locally

```bash
cd backend
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d db                                   # just PostgreSQL
export DATABASE_URL=postgresql+psycopg://arena:arena@localhost:5432/arena   # expose port 5432 in compose or use SQLite:
export DATABASE_URL=sqlite:///./dev.db DATA_DIR=./data TEACHER_SECRET=dev
alembic upgrade head
uvicorn app.main:app --reload --port 8000                 # API (frontend served if backend/static exists)
python -m app.worker                                      # in a second terminal
```

With `RUNNER_MOUNT_MODE=bind` (default outside Docker) the worker bind-mounts `DATA_DIR`
directly; the sandbox image must exist (`make runner`).

### 9.3 Frontend locally

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to http://localhost:8000
npm run typecheck
npm run build        # -> frontend/dist (copied to backend/static by the Dockerfile)
```

No Node installed? `make typecheck` runs `tsc` in a Node container.

### 9.4 Database migrations

```bash
make migration m="add something"     # autogenerate inside the web container
make migrate                         # apply
```

Migrations run automatically when the `web` container starts.

### 9.5 Formatting / linting

```bash
make lint                             # ruff format --check + ruff check (backend)
cd backend && ruff format . && ruff check --fix .
```

### 9.6 Windows

`make` is usually not available; use `.\scripts\arena.ps1 <target>` (same names) or the
`docker compose ...` commands listed next to each Makefile target.

---

## 10. Testing

```bash
make test          # full suite inside the worker container (has Docker access -> sandbox tests run)
make test-local    # local virtualenv; sandbox tests are skipped unless Docker + runner image exist
cd backend && pytest -m "not docker"   # skip sandbox tests explicitly
```

Coverage:

* **submission validation** — valid CSV, BOM/column order, missing rows, duplicate ids, unknown
  ids/datasets, NaN/Inf/out-of-range probabilities, missing columns, empty file, oversized
  uploads (413), malicious ZIPs (traversal, absolute paths, symlinks, too many files, zip bombs
  with lying headers).
* **evaluation** — accuracy/log loss match scikit-learn on known predictions; perfect/inverted
  predictions; a hand-made rule on the real hidden set.
* **Python runner** (`-m docker`) — minimal torch submission succeeds; syntax error, runtime
  error and wrong shape are reported; an infinite loop is terminated by the timeout and the
  container is removed; no network; hidden labels/secrets are not reachable; filesystem is
  read-only except `/tmp`; runs as non-root.
* **API** — join, submit, 429 flood protection, status transitions via the worker, result and
  display retrieval, score hiding, teacher auth, session controls, event log replay, reset/delete.
* **modularity** — `test_dummy_challenge.py` registers a different adapter/evaluator/
  visualization triple and runs it through the unchanged platform.

Tests use SQLite by default; set `TEST_DATABASE_URL=postgresql+psycopg://...` to run them
against PostgreSQL.

---

## 11. Configuration reference

All settings come from environment variables / `.env` (see `.env.example` and
`backend/app/config.py`):

| variable | default | meaning |
|---|---|---|
| `TEACHER_SECRET` | `change-me` | teacher login |
| `ARENA_PORT` | `8000` | published port |
| `POSTGRES_PASSWORD` | `arena` | database password |
| `MAX_UPLOAD_BYTES` | 50 MB | upload cap |
| `SUBMISSION_MIN_INTERVAL_SECONDS` | 5 | per-participant minimum spacing |
| `MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` | 1 | queued/running submissions allowed per student |
| `ZIP_MAX_FILES` / `ZIP_MAX_UNCOMPRESSED_BYTES` | 500 / 200 MB | ZIP hardening |
| `RUNNER_IMAGE` | `dnnls-arena-runner:latest` | sandbox image |
| `RUNNER_TIMEOUT_SECONDS` | 30 | wall-clock limit |
| `RUNNER_CPUS` / `RUNNER_MEMORY` / `RUNNER_PIDS_LIMIT` / `RUNNER_TMP_SIZE` | 1.0 / 512m / 64 / 256m | resource limits |
| `RUNNER_MOUNT_MODE` | `auto` | `volume` (compose) or `bind` (local) |
| `RUNNER_DATA_VOLUME` / `RUNNER_VOLUME_MOUNTPOINT` / `RUNNER_HOST_DATA_DIR` | – / `/data` / – | see §6 |
| `SSE_POLL_INTERVAL_SECONDS` / `SSE_HEARTBEAT_SECONDS` | 0.5 / 15 | live update cadence |
| `WORKER_POLL_INTERVAL_SECONDS` / `STALE_JOB_SECONDS` | 1 / 600 | worker behaviour |
| `LOG_LEVEL` | INFO | logging |

---

## 12. Security notes

* Hidden labels exist only in challenge code (`hidden_targets()`); they are never written to
  the data directory, never mounted into sandboxes and never served by any endpoint.
* Uploads are stored under server-generated UUID paths; original filenames are sanitised and
  only used for display and extension detection.
* Participant tokens are random (256-bit) and stored hashed. The teacher secret is compared
  with a constant-time comparison and never sent to the frontend bundle.
* Unhandled errors return a generic message; details go to the server log. Validation errors
  shown to students contain only information about their own file.
* The Docker socket is mounted **only** into the worker container, never exposed through the
  API or the browser.
* "Hide scores" removes numbers/ranks from student-facing responses and the UI; the projector
  snapshot still contains scores (blob positions need them). It is a classroom convenience,
  not an access control.
* No personal data beyond a self-chosen display name (and an optional student identifier) is
  collected.

---

## 13. Troubleshooting

| symptom | what to check |
|---|---|
| `docker compose up` fails building the runner image | network access to PyPI / download.pytorch.org; disk space (image ≈ 1.5 GB) |
| ZIP submissions fail with "runner image … is not available" | `docker compose build runner-builder` then `docker compose restart worker` |
| ZIP submissions fail with a mount error mentioning `volume-subpath` | Docker Engine < 25. Upgrade Docker, or set `RUNNER_MOUNT_MODE=bind` and `RUNNER_HOST_DATA_DIR=<host path>` with a bind-mounted data directory |
| Students cannot connect but `localhost:8000` works | firewall (UFW / Windows Defender), wrong IP, or Wi-Fi client isolation (§3.2) |
| Projector shows "reconnecting…" | the browser lost the SSE stream; it reconnects automatically. Check `docker compose logs web` |
| Submission stuck in "queued" | worker not running: `docker compose ps`, `docker compose logs worker` |
| Reset everything | `docker compose down -v && docker compose up -d --build` |
