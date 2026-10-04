from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from app.core import RegistryError, challenges
from app.schemas.api import ChallengeDetail, ChallengeSummary, DisplayOut
from app.services.live import challenge_summary, session_display

router = APIRouter(prefix="/challenges", tags=["challenges"])


def _get(challenge_id: str):
    try:
        return challenges.get(challenge_id)
    except RegistryError:
        raise HTTPException(404, "Challenge not found.") from None


@router.get("", response_model=list[ChallengeSummary])
def list_challenges():
    return [challenge_summary(c) for c in challenges]


@router.get("/{challenge_id}", response_model=ChallengeDetail)
def get_challenge(challenge_id: str):
    ch = _get(challenge_id)
    return {**ch.detail(), **challenge_summary(ch)}


@router.get("/{challenge_id}/display", response_model=DisplayOut)
def get_challenge_display(challenge_id: str):
    _get(challenge_id)
    return session_display(challenge_id)


@router.get("/{challenge_id}/resources/{name}")
def download_resource(challenge_id: str, name: str):
    ch = _get(challenge_id)
    res = ch.get_resource(name)
    if res is None:
        raise HTTPException(404, "Resource not found.")
    return Response(
        content=res.loader(),
        media_type=res.content_type,
        headers={"Content-Disposition": f'attachment; filename="{res.name}"'},
    )
