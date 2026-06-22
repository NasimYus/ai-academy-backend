from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

# Token "purposes" let us reuse JWT for access + email verification.
ACCESS = "access"
VERIFY_EMAIL = "verify_email"

# bcrypt operates on at most 72 bytes; longer inputs are truncated by spec.
_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_token(subject: str, purpose: str = ACCESS, expires_minutes: int | None = None) -> str:
    minutes = expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "purpose": purpose,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str, expected_purpose: str = ACCESS) -> str | None:
    """Return the subject if the token is valid and matches the purpose, else None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != expected_purpose:
        return None
    return payload.get("sub")
