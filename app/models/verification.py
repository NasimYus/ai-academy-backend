from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Verification(Base):
    """Email/SMS verification codes, parity of the legacy `verifications` table.

    Legacy stored epoch ints; we use timestamptz. Code TTL is 1 hour.
    """

    __tablename__ = "verifications"

    EXPIRE_SECONDS = 3600  # 1 hour, mirrors Verification::EXPIRE_TIME

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    mobile: Mapped[str | None] = mapped_column(String(16))
    email: Mapped[str | None] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
