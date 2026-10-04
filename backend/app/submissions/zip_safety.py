"""Hardened ZIP extraction: no traversal, no absolute paths, no symlinks, bounded size/count."""

from __future__ import annotations

import os
import posixpath
import stat
import zipfile
import zlib
from pathlib import Path

from app.core.submission_adapter import SubmissionError

_CHUNK = 1024 * 1024


def _normalise_member_name(name: str) -> str:
    # ZIP archives created on Windows can contain backslashes.
    name = name.replace("\\", "/")
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        raise SubmissionError("ZIP archive contains an absolute path.", [name])
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise SubmissionError("ZIP archive contains a path traversal entry.", [name])
    return "/".join(parts)


def safe_extract_zip(
    zip_path: Path,
    dest: Path,
    *,
    max_files: int = 500,
    max_total_uncompressed: int = 200 * 1024 * 1024,
    max_ratio: float = 200.0,
) -> list[str]:
    """Extract ``zip_path`` into ``dest`` and return the relative paths written."""
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise SubmissionError("File is not a valid ZIP archive.", [str(exc)]) from None

    written: list[str] = []
    with zf:
        members = zf.infolist()
        if len(members) > max_files:
            raise SubmissionError(
                f"ZIP archive has too many entries ({len(members)} > {max_files})."
            )
        declared_total = sum(m.file_size for m in members)
        if declared_total > max_total_uncompressed:
            raise SubmissionError(
                "ZIP archive is too large when uncompressed "
                f"({declared_total / 1e6:.1f} MB > {max_total_uncompressed / 1e6:.0f} MB)."
            )
        for m in members:
            if (
                m.compress_size > 0
                and m.file_size / m.compress_size > max_ratio
                and m.file_size > 1_000_000
            ):
                raise SubmissionError(
                    "ZIP archive has a suspicious compression ratio.", [m.filename]
                )

        total = 0
        for m in members:
            rel = _normalise_member_name(m.filename)
            mode = (m.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                raise SubmissionError("ZIP archive contains a symbolic link.", [m.filename])
            if not rel:
                continue
            target = (dest / rel).resolve()
            if target != dest and dest not in target.parents:
                raise SubmissionError("ZIP entry escapes the extraction directory.", [m.filename])
            if m.is_dir() or m.filename.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Never follow a pre-existing symlink in the destination tree.
            if target.parent.is_symlink() or target.is_symlink():
                raise SubmissionError("ZIP entry targets a symbolic link.", [m.filename])
            try:
                with zf.open(m) as src, open(target, "wb") as dst:
                    while True:
                        chunk = src.read(_CHUNK)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_total_uncompressed:
                            raise SubmissionError(
                                "ZIP archive exceeds the uncompressed size limit while extracting."
                            )
                        dst.write(chunk)
            except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError, zlib.error) as exc:
                raise SubmissionError(
                    "ZIP archive is corrupt or inconsistent.", [m.filename, str(exc)]
                ) from None
            os.chmod(target, 0o644)
            written.append(posixpath.normpath(rel))
    return written
