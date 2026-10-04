from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DB, CurrentParticipant, IsTeacher, get_session_or_404
from app.core import challenges
from app.models import ClassSession, SessionEvent, Submission
from app.schemas.api import JoinRequest, JoinResponse, LiveSnapshot, MeResponse, SessionPublic
from app.services import live as live_svc
from app.services import sessions as svc

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/join", response_model=JoinResponse, status_code=status.HTTP_201_CREATED)
def join(payload: JoinRequest, db: DB):
    session = db.scalar(
        select(ClassSession).where(ClassSession.join_code == payload.join_code.strip().upper())
    )
    if session is None:
        raise HTTPException(404, "No session with that join code.")
    participant, token = svc.join_session(
        db, session, payload.display_name, payload.student_identifier
    )
    db.commit()
    return {
        "token": token,
        "participant": live_svc.participant_live(db, participant),
        "session": svc.session_public(session),
    }


@router.get("/by-code/{join_code}", response_model=SessionPublic)
def session_by_code(join_code: str, db: DB):
    session = db.scalar(
        select(ClassSession).where(ClassSession.join_code == join_code.strip().upper())
    )
    if session is None:
        raise HTTPException(404, "No session with that join code.")
    return svc.session_public(session)


@router.get("/me", response_model=MeResponse)
def me(db: DB, participant: CurrentParticipant, teacher: IsTeacher):
    session = db.get(ClassSession, participant.session_id)
    challenge = challenges.get(session.challenge_id)
    snapshot = live_svc.live_snapshot(db, session)
    mine = next(p for p in snapshot["participants"] if p["id"] == str(participant.id))
    hide = session.scores_hidden and not teacher
    subs = db.scalars(
        select(Submission)
        .where(Submission.participant_id == participant.id)
        .order_by(Submission.created_at.desc())
    ).all()
    if hide:
        mine = {
            **mine,
            "best_score": None,
            "best_metrics": None,
            "latest_score": None,
            "rank": None,
        }
    return {
        "participant": mine,
        "session": svc.session_public(session),
        "challenge": live_svc.challenge_summary(challenge),
        "submissions": [live_svc.submission_public(s, include_scores=not hide) for s in subs],
        "scores_hidden": hide,
    }


@router.get("/{session_id}", response_model=SessionPublic)
def get_session(session_id: uuid.UUID, db: DB):
    return svc.session_public(get_session_or_404(db, session_id))


@router.get("/{session_id}/live", response_model=LiveSnapshot)
def get_live(session_id: uuid.UUID, db: DB):
    """Full snapshot for the projector (scores included; the UI hides numbers when asked)."""
    session = get_session_or_404(db, session_id)
    snap = live_svc.live_snapshot(db, session)
    last = db.scalar(select(func.max(SessionEvent.id)).where(SessionEvent.session_id == session.id))
    return {**snap, "last_event_id": int(last or 0)}
