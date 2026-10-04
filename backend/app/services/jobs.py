"""PostgreSQL-backed job queue (works on SQLite for tests; SKIP LOCKED is a no-op there)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import EvaluationJob, Submission


def enqueue(db: Session, submission: Submission) -> EvaluationJob:
    job = EvaluationJob(submission_id=submission.id, status="queued")
    submission.status = "queued"
    db.add(job)
    db.flush()
    return job


def claim_next(db: Session, worker_id: str) -> EvaluationJob | None:
    """Atomically claim the oldest queued job. Caller must commit."""
    stmt = (
        select(EvaluationJob)
        .where(EvaluationJob.status == "queued")
        .order_by(EvaluationJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = db.scalar(stmt)
    if job is None:
        return None
    job.status = "running"
    job.attempts += 1
    job.locked_by = worker_id
    job.locked_at = datetime.now(UTC)
    db.flush()
    return job


def requeue_stale(db: Session, older_than_seconds: int) -> int:
    """Return jobs stuck in ``running`` (e.g. worker crashed) to the queue."""
    cutoff = datetime.now(UTC) - timedelta(seconds=older_than_seconds)
    stale = db.scalars(
        select(EvaluationJob).where(
            EvaluationJob.status == "running", EvaluationJob.locked_at < cutoff
        )
    ).all()
    for job in stale:
        job.status = "queued"
        job.locked_by = None
        job.locked_at = None
        job.last_error = "requeued after stale lock"
        db.execute(
            update(Submission).where(Submission.id == job.submission_id).values(status="queued")
        )
    return len(stale)


def finish(db: Session, job_id: uuid.UUID, *, ok: bool, error: str | None = None) -> None:
    job = db.get(EvaluationJob, job_id)
    if job is None:
        return
    job.status = "done" if ok else "failed"
    job.last_error = error
    job.locked_by = None
