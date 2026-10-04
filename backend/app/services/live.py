"""Live snapshot: per-participant aggregates used by the projector and the student page.

Ranking rule (documented in the README): a participant's *best* submission is the succeeded
submission with the best primary score (ties -> the earlier one). Blob position uses the
best score; the participant's "selected" submission defaults to the best one.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core import challenges
from app.models import ClassSession, EvaluationResult, Participant, Submission


def challenge_summary(challenge) -> dict[str, Any]:  # noqa: ANN001
    """Challenge summary enriched with the adapter descriptions it allows."""
    from app.core import adapters

    return {
        **challenge.summary(),
        "submission_types": [
            adapters.get(a).public_info() for a in allowed_submission_types(challenge)
        ],
    }


def allowed_submission_types(challenge) -> list[str]:  # noqa: ANN001
    return list(
        challenge.adapter_config.get("allowed_submission_types") or [challenge.submission_type]
    )


def enabled_submission_types(session: ClassSession) -> list[str]:
    """Effective adapters for a session: the teacher's selection, else everything allowed."""
    allowed = allowed_submission_types(challenges.get(session.challenge_id))
    if session.enabled_submission_types is None:
        return allowed
    return [a for a in allowed if a in session.enabled_submission_types]


def submission_public(sub: Submission, *, include_scores: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": str(sub.id),
        "session_id": str(sub.session_id),
        "participant_id": str(sub.participant_id),
        "seq_no": sub.seq_no,
        "status": sub.status,
        "submission_type": sub.submission_type,
        "original_filename": sub.original_filename,
        "size_bytes": sub.size_bytes,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "started_at": sub.started_at.isoformat() if sub.started_at else None,
        "finished_at": sub.finished_at.isoformat() if sub.finished_at else None,
        "error_message": sub.error_message,
        "error_details": sub.error_details or [],
        "primary_score": None,
        "metrics": None,
    }
    if sub.result is not None and include_scores:
        out["primary_score"] = sub.result.primary_score
        out["metrics"] = sub.result.metrics
    return out


def _better(a: float, b: float, higher_is_better: bool) -> bool:
    return a > b if higher_is_better else a < b


def participant_live(db: Session, participant: Participant) -> dict[str, Any]:
    session = db.get(ClassSession, participant.session_id)
    challenge = challenges.get(session.challenge_id)
    hib = challenge.primary_metric.higher_is_better
    subs = db.scalars(
        select(Submission)
        .where(Submission.participant_id == participant.id)
        .options(selectinload(Submission.result))
        .order_by(Submission.created_at, Submission.seq_no)
    ).all()
    return _aggregate(participant, subs, hib)


def _aggregate(participant: Participant, subs: list[Submission], hib: bool) -> dict[str, Any]:
    best: Submission | None = None
    for s in subs:
        if s.status == "succeeded" and s.result is not None:
            if best is None or _better(s.result.primary_score, best.result.primary_score, hib):
                best = s
    latest = subs[-1] if subs else None
    return {
        "id": str(participant.id),
        "display_name": participant.display_name,
        "joined_at": participant.joined_at.isoformat() if participant.joined_at else None,
        "n_submissions": len(subs),
        "n_succeeded": sum(1 for s in subs if s.status == "succeeded"),
        "best_score": best.result.primary_score if best else None,
        "best_metrics": best.result.metrics if best else None,
        "best_submission_id": str(best.id) if best else None,
        "best_at": best.finished_at.isoformat() if best and best.finished_at else None,
        "latest_submission_id": str(latest.id) if latest else None,
        "latest_status": latest.status if latest else None,
        "latest_at": latest.created_at.isoformat() if latest and latest.created_at else None,
        "latest_score": (
            latest.result.primary_score if latest and latest.result is not None else None
        ),
    }


def rank_participants(parts: list[dict[str, Any]], higher_is_better: bool) -> None:
    """Assign ``rank`` in-place (1 = best). Participants without a score get rank None."""
    scored = [p for p in parts if p["best_score"] is not None]
    scored.sort(
        key=lambda p: (
            (-p["best_score"]) if higher_is_better else p["best_score"],
            p["best_at"] or "",
        )
    )
    for i, p in enumerate(scored, start=1):
        p["rank"] = i
    for p in parts:
        p.setdefault("rank", None)


def live_snapshot(db: Session, session: ClassSession) -> dict[str, Any]:
    from app.services.sessions import session_public  # local import: avoid cycle

    challenge = challenges.get(session.challenge_id)
    participants = db.scalars(
        select(Participant)
        .where(Participant.session_id == session.id)
        .order_by(Participant.joined_at)
    ).all()
    subs = db.scalars(
        select(Submission)
        .where(Submission.session_id == session.id)
        .options(selectinload(Submission.result))
        .order_by(Submission.created_at, Submission.seq_no)
    ).all()
    by_participant: dict[uuid.UUID, list[Submission]] = {p.id: [] for p in participants}
    for s in subs:
        by_participant.setdefault(s.participant_id, []).append(s)
    hib = challenge.primary_metric.higher_is_better
    parts = [_aggregate(p, by_participant.get(p.id, []), hib) for p in participants]
    rank_participants(parts, hib)
    return {
        "session": session_public(session),
        "challenge": challenge_summary(challenge),
        "participants": parts,
    }


def session_display(challenge_id: str) -> dict[str, Any]:
    from app.core import visualizations

    challenge = challenges.get(challenge_id)
    viz = visualizations.get(challenge.visualization)
    return {
        "visualization": challenge.visualization,
        "config": challenge.visualization_config,
        "data": viz.session_display(challenge),
    }


def result_display(result: EvaluationResult) -> dict[str, Any]:
    return result.display_data or {}
