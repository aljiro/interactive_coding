"""Class sessions and participants."""

from __future__ import annotations

import hashlib
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import challenges
from app.models import ClassSession, Participant, Submission
from app.services import events
from app.services.live import enabled_submission_types, participant_live

JOIN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def generate_join_code(db: Session, length: int = 6) -> str:
    for _ in range(50):
        code = "".join(secrets.choice(JOIN_ALPHABET) for _ in range(length))
        if db.scalar(select(ClassSession.id).where(ClassSession.join_code == code)) is None:
            return code
    raise RuntimeError("could not generate a unique join code")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(
    db: Session, challenge_id: str, name: str, join_code: str | None = None
) -> ClassSession:
    challenges.get(challenge_id)  # raises RegistryError if unknown
    session = ClassSession(
        challenge_id=challenge_id,
        name=name.strip() or challenges.get(challenge_id).title,
        join_code=(join_code or generate_join_code(db)).upper(),
    )
    db.add(session)
    db.flush()
    return session


def session_public(session: ClassSession) -> dict:
    ch = challenges.get(session.challenge_id)
    return {
        "id": str(session.id),
        "name": session.name,
        "challenge_id": session.challenge_id,
        "challenge_title": ch.title,
        "join_code": session.join_code,
        "accepting_submissions": session.accepting_submissions,
        "scores_hidden": session.scores_hidden,
        "enabled_submission_types": enabled_submission_types(session),
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


def join_session(
    db: Session, session: ClassSession, display_name: str, student_identifier: str | None
) -> tuple[Participant, str]:
    token = secrets.token_urlsafe(32)
    participant = Participant(
        session_id=session.id,
        display_name=display_name.strip()[:60],
        student_identifier=(student_identifier or "").strip()[:100] or None,
        token_hash=hash_token(token),
    )
    db.add(participant)
    db.flush()
    events.emit(
        db, session.id, "participant_joined", {"participant": participant_live(db, participant)}
    )
    return participant, token


def participant_by_token(db: Session, token: str) -> Participant | None:
    if not token:
        return None
    return db.scalar(select(Participant).where(Participant.token_hash == hash_token(token)))


def session_counts(db: Session, session_id: uuid.UUID) -> dict:
    n_participants = db.scalar(
        select(func.count(Participant.id)).where(Participant.session_id == session_id)
    )
    n_submissions = db.scalar(
        select(func.count(Submission.id)).where(Submission.session_id == session_id)
    )
    return {"n_participants": int(n_participants or 0), "n_submissions": int(n_submissions or 0)}


def reset_session(db: Session, session: ClassSession) -> None:
    """Remove all participants and submissions, keep the session and join code."""
    for p in list(session.participants):
        db.delete(p)
    for s in list(session.submissions):
        db.delete(s)
    db.flush()
    events.emit(db, session.id, "session_reset", {})


def delete_session(db: Session, session: ClassSession) -> None:
    events.emit(db, session.id, "session_deleted", {})
    db.flush()
    db.delete(session)
