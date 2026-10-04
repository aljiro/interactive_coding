"""Upload storage: server-generated paths, size caps, sanitised original names."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import Settings

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class UploadTooLarge(Exception):
    pass


def sanitize_filename(name: str | None, fallback: str = "upload") -> str:
    base = Path(name or "").name
    base = _SAFE.sub("_", base).strip("._") or fallback
    return base[:120]


def submission_dir(settings: Settings, submission_id: uuid.UUID) -> Path:
    return settings.submissions_dir / str(submission_id)


async def save_upload(
    settings: Settings, submission_id: uuid.UUID, upload: UploadFile, ext: str
) -> tuple[Path, int]:
    """Stream the upload to disk under a server-chosen name; abort if it exceeds the cap."""
    target_dir = submission_dir(settings, submission_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"artifact{ext}"
    size = 0
    limit = settings.max_upload_bytes
    with open(target, "wb") as fh:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                fh.close()
                target.unlink(missing_ok=True)
                raise UploadTooLarge(f"Upload exceeds the {limit // (1024 * 1024)} MB limit.")
            fh.write(chunk)
    return target, size
