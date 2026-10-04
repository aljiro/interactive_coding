"""Append events to the per-session log (consumed by the SSE endpoint)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import SessionEvent


def emit(
    db: Session, session_id: uuid.UUID, event_type: str, payload: dict[str, Any]
) -> SessionEvent:
    ev = SessionEvent(session_id=session_id, type=event_type, payload=payload)
    db.add(ev)
    db.flush()
    return ev
