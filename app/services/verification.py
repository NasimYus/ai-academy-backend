"""Verification code flow — parity port of the legacy VerificationController.

`check_confirmed` issues/refreshes a code (or short-circuits when verification
is disabled); `confirm_code` validates a submitted code and activates the user.
Code delivery (SMS/email) is a no-op outside production until the email/SMS
infrastructure lands (F.2/F.3); in debug the code is surfaced to the caller.
"""

import random
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User, UserStatus
from app.models.verification import Verification
from app.services import email

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$", re.IGNORECASE)


def detect_field(value: str) -> str:
    """'email' if it looks like an email, else 'mobile' (mirrors legacy regex)."""
    return "email" if _EMAIL_RE.match(value or "") else "mobile"


def _new_code() -> str:
    return str(random.randint(10000, 99999))


def _now() -> datetime:
    return datetime.now(UTC)


async def check_confirmed(
    db: AsyncSession, *, user: User | None, field: str, value: str
) -> dict[str, str | None]:
    """Returns {"status": "verified"} or {"status": "send", "code": <dev only>}."""
    if settings.disable_registration_verification_process:
        return {"status": "verified"}

    value = value.lstrip("+")
    now = _now()
    expire = timedelta(seconds=Verification.EXPIRE_SECONDS)

    column = getattr(Verification, field)
    result = await db.execute(
        select(Verification)
        .where(column == value, Verification.expired_at > now)
        .order_by(Verification.id.desc())
    )
    verification = result.scalars().first()

    if verification is not None:
        if verification.verified_at is not None:
            return {"status": "verified"}
        old_expired = verification.expired_at
        verification.created_at = now
        verification.expired_at = now + expire
        if old_expired is None or now > old_expired:
            verification.code = _new_code()
        verification.verified_at = None
    else:
        verification = Verification(
            code=_new_code(),
            user_id=user.id if user is not None else None,
            created_at=now,
            expired_at=now + expire,
        )
        setattr(verification, field, value)
        db.add(verification)

    await db.commit()
    await db.refresh(verification)
    await _deliver(verification, field)

    return {"status": "send", "code": verification.code if settings.debug else None}


async def confirm_code(db: AsyncSession, *, value: str, code: str) -> bool:
    """Validate a code and activate the matching user. Returns True on success."""
    field = detect_field(value)
    value = value.lstrip("+") if field == "mobile" else value
    now = _now()
    column = getattr(Verification, field)

    # Mark a fresh (<24h), unverified, matching code as verified.
    await db.execute(
        update(Verification)
        .where(
            column == value,
            Verification.verified_at.is_(None),
            Verification.code == code,
            Verification.created_at > now - timedelta(hours=24),
        )
        .values(verified_at=now, expired_at=now + timedelta(seconds=50))
    )

    valid = await db.execute(
        select(Verification.id).where(
            column == value,
            Verification.code == code,
            Verification.verified_at.is_not(None),
            Verification.expired_at > now,
        )
    )
    if valid.first() is None:
        await db.commit()
        return False

    result = await db.execute(select(User).where(getattr(User, field) == value))
    user = result.scalar_one_or_none()
    if user is not None:
        # TODO(Phase 5): apply referral code here when affiliates land.
        user.status = UserStatus.active
    await db.commit()
    return True


async def _deliver(verification: Verification, field: str) -> None:
    """Deliver the verification code. Email is sent via the email service (F.3);
    SMS delivery is still deferred (no provider yet)."""
    if field != "email":
        return  # TODO(F.3): SMS provider for mobile verification
    await email.send_email(
        to=verification.email,
        subject="Код подтверждения — AI Academy",
        body=(
            f"Ваш код подтверждения: {verification.code}\n\n"
            "Код действует ограниченное время. Если вы не запрашивали его, проигнорируйте письмо."
        ),
    )
