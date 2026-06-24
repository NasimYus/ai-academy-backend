from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Newsletter(Base):
    """A newsletter subscription, parity of legacy `newsletters`.

    `user_id` is set only when an authenticated user subscribes with their own
    email (legacy makeNewsletter). Email is unique (legacy unique validation).
    NewsletterHistory (admin send-side) is Phase 6 / admin.
    """

    __tablename__ = "newsletters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
