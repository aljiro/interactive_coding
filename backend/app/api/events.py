"""Server-Sent Events: streams rows of ``session_events`` for one session.

Each connection polls the event table (cheap indexed query) and forwards new rows. Clients
resume with ``Last-Event-ID`` (or ``?after=``) after reconnecting.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import DB, Cfg, get_session_or_404
from app.db import SessionLocal
from app.models import SessionEvent

router = APIRouter(tags=["events"])


def _fetch(session_id: uuid.UUID, after: int, limit: int = 200) -> list[SessionEvent]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(SessionEvent)
            .where(SessionEvent.session_id == session_id, SessionEvent.id > after)
            .order_by(SessionEvent.id)
            .limit(limit)
        ).all()
        db.expunge_all()
        return rows


def _format(ev: SessionEvent) -> str:
    data = json.dumps(ev.payload, separators=(",", ":"))
    return f"id: {ev.id}\nevent: {ev.type}\ndata: {data}\n\n"


@router.get("/sessions/{session_id}/events")
async def session_events(
    session_id: uuid.UUID,
    request: Request,
    db: DB,
    settings: Cfg,
    after: int | None = None,
    once: bool = False,
    last_event_id: Annotated[str | None, Header()] = None,
):
    """Stream session events as SSE. ``once=true`` returns the backlog and closes (debugging)."""
    get_session_or_404(db, session_id)
    cursor = 0
    if last_event_id and last_event_id.isdigit():
        cursor = int(last_event_id)
    elif after is not None:
        cursor = after

    async def stream():
        nonlocal cursor
        yield "retry: 2000\n\n"
        idle = 0.0
        while True:
            if await request.is_disconnected():
                break
            rows = await asyncio.to_thread(_fetch, session_id, cursor)
            if rows:
                for ev in rows:
                    cursor = ev.id
                    yield _format(ev)
                    if ev.type == "session_deleted":
                        return
                idle = 0.0
                if once:
                    return
            else:
                if once:
                    return
                idle += settings.sse_poll_interval_seconds
                if idle >= settings.sse_heartbeat_seconds:
                    idle = 0.0
                    yield ": keep-alive\n\n"
            await asyncio.sleep(settings.sse_poll_interval_seconds)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
