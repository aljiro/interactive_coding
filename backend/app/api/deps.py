from __future__ import annotations

import secrets
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import ClassSession, Participant
from app.services.sessions import participant_by_token

DB = Annotated[Session, Depends(get_db)]
Cfg = Annotated[Settings, Depends(get_settings)]


def require_teacher(
    settings: Cfg, x_teacher_secret: Annotated[str | None, Header()] = None
) -> None:
    if not x_teacher_secret or not secrets.compare_digest(
        x_teacher_secret, settings.teacher_secret
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Teacher secret required.")


def is_teacher(settings: Cfg, x_teacher_secret: Annotated[str | None, Header()] = None) -> bool:
    return bool(x_teacher_secret) and secrets.compare_digest(
        x_teacher_secret, settings.teacher_secret
    )


Teacher = Annotated[None, Depends(require_teacher)]
IsTeacher = Annotated[bool, Depends(is_teacher)]


def current_participant(
    db: DB, x_participant_token: Annotated[str | None, Header()] = None
) -> Participant:
    participant = participant_by_token(db, x_participant_token or "")
    if participant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Participant token missing or invalid.")
    return participant


CurrentParticipant = Annotated[Participant, Depends(current_participant)]


def get_session_or_404(db: Session, session_id: uuid.UUID) -> ClassSession:
    session = db.get(ClassSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    return session
