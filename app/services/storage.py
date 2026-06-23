"""Local file storage (F.1).

Minimal disk-backed storage for uploads. Files are written under
`settings.media_root` and served at `settings.media_url` (mounted in main).
An S3-compatible backend can replace this later behind the same interface.
"""
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


def save_upload(file: UploadFile, subdir: str) -> str:
    """Persist an uploaded file and return its public path (e.g. /media/.../x.png)."""
    ext = Path(file.filename or "").suffix.lower()
    name = f"{uuid.uuid4().hex}{ext}"
    target_dir = Path(settings.media_root) / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    with open(target_dir / name, "wb") as out:
        out.write(file.file.read())

    return f"{settings.media_url}/{subdir}/{name}"
