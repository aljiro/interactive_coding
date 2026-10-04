"""Evaluation worker: claims queued jobs transactionally and evaluates them.

Run with ``python -m app.worker``. Safe to restart at any time: queued jobs stay in the
database, and jobs stuck in ``running`` are requeued after ``STALE_JOB_SECONDS``.
"""

from __future__ import annotations

import logging
import signal
import time

from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.db import SessionLocal
from app.plugins import load_builtin
from app.services import jobs
from app.services.evaluation import process_submission

log = logging.getLogger("worker")
_stop = False


def _handle_signal(signum, frame):  # noqa: ANN001
    global _stop
    log.info("signal %s received; finishing current job then exiting", signum)
    _stop = True


def run_once(worker_id: str) -> bool:
    """Claim and process one job. Returns True if a job was processed."""
    with SessionLocal() as db:
        job = jobs.claim_next(db, worker_id)
        if job is None:
            db.rollback()
            return False
        submission_id = job.submission_id
        job_id = job.id
        db.commit()

    log.info("processing submission %s", submission_id)
    with SessionLocal() as db:
        try:
            sub = process_submission(db, submission_id)
            jobs.finish(db, job_id, ok=sub.status == "succeeded", error=sub.error_message)
            db.commit()
            log.info("submission %s -> %s", submission_id, sub.status)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            log.exception("job %s crashed", job_id)
            jobs.finish(db, job_id, ok=False, error=str(exc)[:1000])
            db.commit()
    return True


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    load_builtin()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    worker_id = settings.effective_worker_id
    log.info("worker %s started (poll %.1fs)", worker_id, settings.worker_poll_interval_seconds)

    last_stale_check = 0.0
    while not _stop:
        try:
            if time.monotonic() - last_stale_check > 30:
                with SessionLocal() as db:
                    n = jobs.requeue_stale(db, settings.stale_job_seconds)
                    db.commit()
                    if n:
                        log.warning("requeued %d stale job(s)", n)
                last_stale_check = time.monotonic()
            if not run_once(worker_id):
                time.sleep(settings.worker_poll_interval_seconds)
        except OperationalError as exc:
            log.warning("database unavailable (%s); retrying in 3s", exc.__class__.__name__)
            time.sleep(3)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
