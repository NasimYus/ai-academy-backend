import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class RewardStatus(str, enum.Enum):
    """Legacy `rewards_accounting.status` (addiction = earned, deduction = spent)."""

    addiction = "addiction"
    deduction = "deduction"


class RewardAccounting(Base):
    """A points ledger entry, parity of legacy `rewards_accounting`.

    `type` is the event label (registration / buy / passed_quiz / withdraw …);
    kept as a free string (legacy enum merges Reward types + 'withdraw').
    `item_id` references the related entity (course/quiz/…) for de-duplication.
    The reward-earning rules (Reward table) are settings-gated and deferred.
    """

    __tablename__ = "rewards_accounting"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item_id: Mapped[int | None] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RewardStatus] = mapped_column(
        Enum(RewardStatus, name="reward_status"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", lazy="raise")
