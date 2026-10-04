"""Teacher/admin endpoints (protected by the X-Teacher-Secret header)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DB, Teacher, get_session_or_404
from app.core import RegistryError, challenges
from app.models import ClassSession, Submission
from app.schemas.api import (
    Message,
    SessionCreate,
    SessionPublic,
    SessionTeacherView,
    SessionUpdate,
    SubmissionPublic,
)
from app.services import events
from app.services import sessions as svc
from app.services.live import allowed_submission_types, submission_public

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/verify", response_model=Message)
def verify(_: Teacher):
    return {"detail": "ok"}


@router.get("/sessions", response_model=list[SessionTeacherView])
def list_sessions(_: Teacher, db: DB):
    rows = db.scalars(select(ClassSession).order_by(ClassSession.created_at.desc())).all()
    return [{**svc.session_public(s), **svc.session_counts(db, s.id)} for s in rows]


@router.post("/sessions", response_model=SessionPublic, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, _: Teacher, db: DB):
    try:
        session = svc.create_session(db, payload.challenge_id, payload.name, payload.join_code)
    except RegistryError as exc:
        raise HTTPException(404, str(exc)) from None
    db.commit()
    return svc.session_public(session)


@router.patch("/sessions/{session_id}", response_model=SessionPublic)
def update_session(session_id: uuid.UUID, payload: SessionUpdate, _: Teacher, db: DB):
    session = get_session_or_404(db, session_id)
    if payload.name is not None and payload.name.strip():
        session.name = payload.name.strip()
    if payload.accepting_submissions is not None:
        session.accepting_submissions = payload.accepting_submissions
    if payload.scores_hidden is not None:
        session.scores_hidden = payload.scores_hidden
    if payload.enabled_submission_types is not None:
        allowed = allowed_submission_types(challenges.get(session.challenge_id))
        unknown = [t for t in payload.enabled_submission_types if t not in allowed]
        if unknown:
            raise HTTPException(
                422, f"Unknown submission type(s) for this challenge: {', '.join(unknown)}"
            )
        if not payload.enabled_submission_types:
            raise HTTPException(
                422,
                "At least one submission type must stay enabled "
                "(use 'stop accepting submissions' to pause).",
            )
        session.enabled_submission_types = [
            t for t in allowed if t in payload.enabled_submission_types
        ]
    db.flush()
    events.emit(db, session.id, "session_updated", {"session": svc.session_public(session)})
    db.commit()
    return svc.session_public(session)


@router.post("/sessions/{session_id}/reset", response_model=Message)
def reset_session(session_id: uuid.UUID, _: Teacher, db: DB):
    session = get_session_or_404(db, session_id)
    svc.reset_session(db, session)
    db.commit()
    return {"detail": "session reset"}


@router.delete("/sessions/{session_id}", response_model=Message)
def delete_session(session_id: uuid.UUID, _: Teacher, db: DB):
    session = get_session_or_404(db, session_id)
    svc.delete_session(db, session)
    db.commit()
    return {"detail": "session deleted"}


@router.get("/sessions/{session_id}/failures", response_model=list[SubmissionPublic])
def failures(session_id: uuid.UUID, _: Teacher, db: DB, limit: int = 100):
    session = get_session_or_404(db, session_id)
    rows = db.scalars(
        select(Submission)
        .where(Submission.session_id == session.id, Submission.status.in_(("failed", "timed_out")))
        .order_by(Submission.created_at.desc())
        .limit(limit)
    ).all()
    return [submission_public(s) for s in rows]
