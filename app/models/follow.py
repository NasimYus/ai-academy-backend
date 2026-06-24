import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FollowStatus(str, enum.Enum):
    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"


class Follow(Base):
    """A follower→user relationship, parity of legacy `follows`.

    The public follow flow creates an `accepted` row directly (no request/approval
    step is used by the user-facing endpoint).
    """

    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "user_id", name="uq_follow_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[FollowStatus] = mapped_column(
        Enum(FollowStatus, name="follow_status"), default=FollowStatus.accepted, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
