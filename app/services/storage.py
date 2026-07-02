"""Local file storage (F.1).

Minimal disk-backed storage for uploads. Files are written under
`settings.media_root` and served at `settings.media_url` (mounted in main).
An S3-compatible backend can replace this later behind the same interface.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

# Reject executable/script uploads (served as static, but defence-in-depth).
_BLOCKED_EXTENSIONS = {
    ".php",
    ".phtml",
    ".php3",
    ".php4",
    ".php5",
    ".pl",
    ".py",
    ".rb",
    ".sh",
    ".bash",
    ".exe",
    ".bat",
    ".cmd",
    ".com",
    ".cgi",
    ".jsp",
    ".asp",
    ".aspx",
    ".js",
    ".mjs",
    ".html",
    ".htm",
    ".svg",  # can carry inline scripts
}

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB


def save_upload(file: UploadFile, subdir: str) -> str:
    """Persist an uploaded file and return its public path (e.g. /media/.../x.png).

    Rejects executable/script extensions and oversized files (→ 422)."""
    ext = Path(file.filename or "").suffix.lower()
    if ext in _BLOCKED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="file_type_not_allowed"
        )

    data = file.file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="file_too_large"
        )

    name = f"{uuid.uuid4().hex}{ext}"
    target_dir = Path(settings.media_root) / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    with open(target_dir / name, "wb") as out:
        out.write(data)

    return f"{settings.media_url}/{subdir}/{name}"
