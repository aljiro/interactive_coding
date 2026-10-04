from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import func, select

from app.api.deps import DB, Cfg, CurrentParticipant, IsTeacher, get_session_or_404
from app.core import SubmissionError, adapters, challenges
from app.models import ClassSession, Submission
from app.schemas.api import SubmissionDisplayOut, SubmissionPublic
from app.services import events, jobs, storage
from app.services.evaluation import choose_adapter
from app.services.live import (
    enabled_submission_types,
    participant_live,
    result_display,
    submission_public,
)

router = APIRouter(tags=["submissions"])


@router.post(
    "/sessions/{session_id}/submissions",
    response_model=SubmissionPublic,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_submission(
    session_id: uuid.UUID,
    db: DB,
    settings: Cfg,
    participant: CurrentParticipant,
    file: Annotated[UploadFile, File(description="Submission artifact")],
):
    session = get_session_or_404(db, session_id)
    if participant.session_id != session.id:
        raise HTTPException(403, "You are not a participant of this session.")
    if not session.accepting_submissions:
        raise HTTPException(409, "This session is not accepting submissions right now.")

    # Simple per-participant flood protection.
    pending = db.scalar(
        select(func.count(Submission.id)).where(
            Submission.participant_id == participant.id,
            Submission.status.in_(("uploaded", "queued", "running")),
        )
    )
    if pending and pending >= settings.max_pending_submissions_per_participant:
        raise HTTPException(429, "Your previous submission is still being evaluated. Please wait.")
    last_at = db.scalar(
        select(func.max(Submission.created_at)).where(Submission.participant_id == participant.id)
    )
    if last_at is not None:
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=UTC)
        wait = timedelta(seconds=settings.submission_min_interval_seconds) - (
            datetime.now(UTC) - last_at
        )
        if wait.total_seconds() > 0:
            raise HTTPException(
                429, f"Please wait {int(wait.total_seconds()) + 1} s before submitting again."
            )

    filename = storage.sanitize_filename(file.filename)
    try:
        adapter_id = choose_adapter(
            session.challenge_id, filename, enabled_submission_types(session)
        )
    except SubmissionError as exc:
        raise HTTPException(422, exc.message) from None
    ext = Path(filename).suffix.lower()

    seq = db.scalar(
        select(func.max(Submission.seq_no)).where(Submission.participant_id == participant.id)
    )
    sub = Submission(
        session_id=session.id,
        participant_id=participant.id,
        seq_no=int(seq or 0) + 1,
        status="uploaded",
        submission_type=adapter_id,
        original_filename=filename,
        artifact_path="",
    )
    db.add(sub)
    db.flush()
    try:
        path, size = await storage.save_upload(settings, sub.id, file, ext)
    except storage.UploadTooLarge as exc:
        db.rollback()
        raise HTTPException(413, str(exc)) from None
    sub.artifact_path = str(path)
    sub.size_bytes = size
    jobs.enqueue(db, sub)
    db.flush()
    events.emit(
        db,
        session.id,
        "submission_updated",
        {
            "submission": submission_public(sub),
            "participant": {**participant_live(db, participant), "improved": False},
        },
    )
    db.commit()
    db.refresh(sub)
    return submission_public(sub)


@router.get("/sessions/{session_id}/submissions", response_model=list[SubmissionPublic])
def list_submissions(
    session_id: uuid.UUID,
    db: DB,
    teacher: IsTeacher,
    participant_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    limit: int = 200,
):
    session = get_session_or_404(db, session_id)
    stmt = select(Submission).where(Submission.session_id == session.id)
    if participant_id is not None:
        stmt = stmt.where(Submission.participant_id == participant_id)
    if status_filter:
        stmt = stmt.where(Submission.status == status_filter)
    stmt = stmt.order_by(Submission.created_at.desc()).limit(min(limit, 1000))
    include_scores = teacher or not session.scores_hidden
    return [submission_public(s, include_scores=include_scores) for s in db.scalars(stmt).all()]


@router.get("/submissions/{submission_id}", response_model=SubmissionPublic)
def get_submission(submission_id: uuid.UUID, db: DB, teacher: IsTeacher):
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(404, "Submission not found.")
    session = db.get(ClassSession, sub.session_id)
    return submission_public(sub, include_scores=teacher or not session.scores_hidden)


@router.get("/submissions/{submission_id}/display", response_model=SubmissionDisplayOut)
def get_submission_display(submission_id: uuid.UUID, db: DB):
    sub = db.get(Submission, submission_id)
    if sub is None or sub.result is None:
        raise HTTPException(404, "No evaluated result for this submission.")
    challenge = challenges.get(db.get(ClassSession, sub.session_id).challenge_id)
    return {
        "submission_id": str(sub.id),
        "participant_id": str(sub.participant_id),
        "visualization": challenge.visualization,
        "data": result_display(sub.result),
    }


@router.get("/submission-types", response_model=list[dict])
def list_submission_types():
    return [a.public_info() for a in adapters]
