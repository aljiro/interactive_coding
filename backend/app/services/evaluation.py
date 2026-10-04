"""The generic evaluation pipeline: artifact -> adapter -> evaluator -> result -> event.

Nothing in here knows about a specific challenge; everything is resolved via registries.
"""

from __future__ import annotations

import logging
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core import SubmissionError, adapters, challenges, evaluators, visualizations
from app.core.submission_adapter import AdapterContext
from app.models import ClassSession, EvaluationResult, Participant, Submission
from app.services import events
from app.services.live import participant_live, submission_public

log = logging.getLogger(__name__)


def choose_adapter(challenge_id: str, filename: str, enabled: list[str] | None = None) -> str:
    """Pick the adapter for an upload by extension among the adapters enabled for the session."""
    from app.services.live import allowed_submission_types

    challenge = challenges.get(challenge_id)
    allowed = allowed_submission_types(challenge)
    candidates = [a for a in allowed if enabled is None or a in enabled]
    ext = Path(filename).suffix.lower()
    for adapter_id in candidates:
        if ext in adapters.get(adapter_id).accepted_extensions:
            return adapter_id
    if not candidates:
        raise SubmissionError("No submission type is currently enabled for this session.")
    accepted = sorted({e for a in candidates for e in adapters.get(a).accepted_extensions})
    disabled = [
        adapters.get(a).label
        for a in allowed
        if a not in candidates
        if ext in adapters.get(a).accepted_extensions
    ]
    hint = f" {disabled[0]} submissions are currently disabled by the teacher." if disabled else ""
    raise SubmissionError(
        f"Unsupported file type '{ext or '(none)'}'. Accepted: {', '.join(accepted)}.{hint}"
    )


def process_submission(
    db: Session, submission_id: uuid.UUID, settings: Settings | None = None
) -> Submission:
    """Evaluate one submission end-to-end and persist the outcome. Commits."""
    settings = settings or get_settings()
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise LookupError(f"submission {submission_id} not found")
    session = db.get(ClassSession, sub.session_id)
    challenge = challenges.get(session.challenge_id)

    sub.status = "running"
    sub.started_at = datetime.now(UTC)
    sub.error_message = None
    sub.error_details = None
    db.commit()
    _emit_update(db, sub)
    db.commit()

    workdir = Path(sub.artifact_path).parent
    try:
        adapter = adapters.get(sub.submission_type)
        ctx = AdapterContext(
            challenge=challenge, inputs=challenge.inputs(), workdir=workdir, settings=settings
        )
        predictions = adapter.run(Path(sub.artifact_path), ctx)
        evaluator = evaluators.get(challenge.evaluator)
        output = evaluator.evaluate(
            predictions, challenge.hidden_targets(), challenge.evaluator_config
        )
        viz = visualizations.get(challenge.visualization)
        display = viz.submission_display(predictions, challenge)
    except SubmissionError as exc:
        sub.status = exc.status
        sub.error_message = exc.message
        sub.error_details = exc.details[:30]
        log.info("submission %s %s: %s", sub.id, sub.status, exc.message)
    except Exception:  # noqa: BLE001 - never let a student artifact crash the worker
        sub.status = "failed"
        sub.error_message = (
            "Internal error while evaluating the submission. The teacher can see details."
        )
        sub.error_details = [traceback.format_exc()[-3000:]]
        log.exception("internal error evaluating submission %s", sub.id)
    else:
        if sub.result is not None:
            db.delete(sub.result)
            db.flush()
        metrics = dict(output.metrics)
        metrics.setdefault("submitted_at", sub.created_at.isoformat() if sub.created_at else None)
        if "runtime_seconds" in predictions.info:
            metrics.setdefault("runtime_seconds", predictions.info["runtime_seconds"])
        db.add(
            EvaluationResult(
                submission_id=sub.id,
                primary_score=float(output.primary_score),
                metrics=metrics,
                display_data=display,
            )
        )
        sub.status = "succeeded"
    sub.finished_at = datetime.now(UTC)
    db.flush()
    db.refresh(sub)
    _emit_update(db, sub)
    db.commit()
    return sub


def _emit_update(db: Session, sub: Submission) -> None:
    participant = db.get(Participant, sub.participant_id)
    before = _best_before(db, participant, sub)
    live = participant_live(db, participant)
    improved = (
        sub.status == "succeeded"
        and live["best_submission_id"] == str(sub.id)
        and (before is None or live["best_score"] != before)
    )
    events.emit(
        db,
        sub.session_id,
        "submission_updated",
        {
            "submission": submission_public(sub),
            "participant": {**live, "improved": improved},
        },
    )


def _best_before(db: Session, participant: Participant, current: Submission) -> float | None:
    challenge = challenges.get(db.get(ClassSession, participant.session_id).challenge_id)
    hib = challenge.primary_metric.higher_is_better
    best = None
    for s in participant.submissions:
        if s.id == current.id or s.status != "succeeded" or s.result is None:
            continue
        v = s.result.primary_score
        if best is None or (v > best if hib else v < best):
            best = v
    return best
