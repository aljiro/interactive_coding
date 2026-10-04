from fastapi import APIRouter

from app.api import challenges, events, sessions, submissions, teacher

router = APIRouter(prefix="/api")
router.include_router(challenges.router)
router.include_router(sessions.router)
router.include_router(submissions.router)
router.include_router(events.router)
router.include_router(teacher.router)
