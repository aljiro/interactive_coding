"""Deterministic demo: one Moons session with ~12 fake participants.

    python -m app.scripts.seed_demo [--join-code DEMO] [--keep]

Each fake student's predictions come from a simple scikit-learn classifier and are pushed
through the *real* pipeline (prediction CSV -> adapter -> evaluator -> visualization), so the
projector view shows genuine decision surfaces. Runs synchronously; no worker is needed.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime, timedelta

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import ClassSession, Submission
from app.plugins import load_builtin
from app.services import sessions as session_svc
from app.services import storage
from app.services.evaluation import process_submission

log = logging.getLogger("seed_demo")

# (display name, list of models submitted in order; None = an invalid submission)
DEMO_STUDENTS: list[tuple[str, list]] = [
    (
        "Mia",
        [
            lambda: LogisticRegression(),
            lambda: MLPClassifier(hidden_layer_sizes=(32, 32), max_iter=2000, random_state=0),
        ],
    ),
    (
        "Sam",
        [
            lambda: CalibratedClassifierCV(
                SVC(kernel="rbf", C=1.0, gamma="scale"), ensemble=False, cv=5
            )
        ],
    ),
    ("Alex", [lambda: KNeighborsClassifier(n_neighbors=15)]),
    ("Priya", [lambda: RandomForestClassifier(n_estimators=200, random_state=0)]),
    ("Leo", [lambda: LogisticRegression()]),
    ("Noor", [lambda: DecisionTreeClassifier(max_depth=3, random_state=0)]),
    ("Tom", [lambda: GaussianNB()]),
    ("Yuki", [lambda: KNeighborsClassifier(n_neighbors=1)]),
    (
        "Omar",
        [
            lambda: make_pipeline(
                PolynomialFeatures(3), StandardScaler(), LogisticRegression(C=10, max_iter=2000)
            )
        ],
    ),
    ("Elena", [lambda: GradientBoostingClassifier(random_state=0)]),
    ("Chen", ["constant"]),
    ("Ravi", [None]),  # one failed submission (invalid CSV)
    ("Dana", []),  # joined, nothing submitted yet
]


def _csv_text(inputs, probs: dict[str, np.ndarray]) -> str:
    lines = ["dataset,id,probability"]
    for name, ds in inputs.items():
        for i, p in zip(ds.ids, probs[name], strict=True):
            lines.append(f"{name},{int(i)},{float(p):.5f}")
    return "\n".join(lines) + "\n"


def _predict(model_factory, X_train, y_train, inputs) -> dict[str, np.ndarray]:
    if model_factory == "constant":
        rng = np.random.default_rng(7)
        return {n: np.clip(0.5 + rng.normal(0, 0.05, ds.n), 0, 1) for n, ds in inputs.items()}
    model = model_factory()
    model.fit(X_train, y_train)
    return {n: model.predict_proba(ds.X)[:, 1] for n, ds in inputs.items()}


def seed(
    join_code: str = "DEMO", keep: bool = False, session_name: str = "Demo — Two Moons"
) -> str:
    load_builtin()
    settings = get_settings()
    from app.core import challenges

    challenge = challenges.get("moons")
    inputs = challenge.inputs()
    X_train, y_train = __import__(
        "app.challenges.moons.data", fromlist=["training_set"]
    ).training_set()

    with SessionLocal() as db:
        existing = db.scalar(select(ClassSession).where(ClassSession.join_code == join_code))
        if existing is not None and not keep:
            log.info("deleting previous demo session %s", existing.id)
            session_svc.delete_session(db, existing)
            db.commit()
            existing = None
        if existing is not None:
            log.info("keeping existing demo session %s", existing.id)
            return str(existing.id)

        session = session_svc.create_session(db, "moons", session_name, join_code=join_code)
        db.commit()
        session_id = session.id
        t = datetime.now(UTC) - timedelta(minutes=len(DEMO_STUDENTS) * 2)
        for name, models in DEMO_STUDENTS:
            participant, _token = session_svc.join_session(db, session, name, None)
            db.commit()
            for k, factory in enumerate(models):
                t += timedelta(seconds=73)
                sub = Submission(
                    session_id=session_id,
                    participant_id=participant.id,
                    seq_no=k + 1,
                    status="uploaded",
                    submission_type="prediction_csv",
                    original_filename="predictions.csv",
                    artifact_path="",
                    created_at=t,
                )
                db.add(sub)
                db.flush()
                target_dir = storage.submission_dir(settings, sub.id)
                target_dir.mkdir(parents=True, exist_ok=True)
                path = target_dir / "artifact.csv"
                if factory is None:
                    path.write_text("dataset,id,probability\ntest,0,1.7\n")
                else:
                    path.write_text(_csv_text(inputs, _predict(factory, X_train, y_train, inputs)))
                sub.artifact_path = str(path)
                sub.size_bytes = path.stat().st_size
                db.commit()
                sub = process_submission(db, sub.id, settings)
                score = f"{sub.result.primary_score:.3f}" if sub.result else "-"
                log.info("%-6s submission %d -> %-9s score=%s", name, k + 1, sub.status, score)
        return str(session_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--join-code", default="DEMO")
    parser.add_argument(
        "--keep", action="store_true", help="do not recreate an existing demo session"
    )
    parser.add_argument("--name", default="Demo — Two Moons")
    args = parser.parse_args()
    logging.basicConfig(level="INFO", format="%(levelname)s %(name)s: %(message)s")
    session_id = seed(args.join_code.upper(), args.keep, args.name)
    print(f"\nDemo session ready. Join code: {args.join_code.upper()}")
    print(f"Projector view: /live/{session_id}")
    print("Teacher view:   /teacher")


if __name__ == "__main__":
    main()
