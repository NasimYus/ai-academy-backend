import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GiftStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    cancel = "cancel"


class Gift(Base):
    """A gifted course/bundle for a recipient (by email), parity of legacy `gifts`.

    Created pending at checkout; on paid the Sale is linked, status → active, and
    the recipient is enrolled if an account with that email already exists (else
    they redeem it after signing up)."""

    __tablename__ = "gifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )  # sender
    webinar_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"))
    bundle_id: Mapped[int | None] = mapped_column(ForeignKey("bundles.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # recipient name
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)  # recipient email
    description: Mapped[str | None] = mapped_column(Text)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # deliver-on
    viewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[GiftStatus] = mapped_column(
        Enum(GiftStatus, name="gift_status"), default=GiftStatus.pending, nullable=False
    )
    # use_alter breaks the gifts <-> sales FK cycle for create_all.
    sale_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales.id", ondelete="SET NULL", use_alter=True, name="fk_gifts_sale_id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
