import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class RewardStatus(str, enum.Enum):
    """Legacy `rewards_accounting.status` (addiction = earned, deduction = spent)."""

    addiction = "addiction"
    deduction = "deduction"


class RewardType(str, enum.Enum):
    """Legacy Reward::getTypesLists — the events that can earn points."""

    account_charge = "account_charge"
    create_classes = "create_classes"
    buy = "buy"
    pass_the_quiz = "pass_the_quiz"
    certificate = "certificate"
    comment = "comment"
    register = "register"
    review_courses = "review_courses"
    instructor_meeting_reserve = "instructor_meeting_reserve"
    student_meeting_reserve = "student_meeting_reserve"
    newsletters = "newsletters"
    badge = "badge"
    referral = "referral"
    learning_progress_100 = "learning_progress_100"
    charge_wallet = "charge_wallet"
    buy_store_product = "buy_store_product"
    pass_assignment = "pass_assignment"
    make_topic = "make_topic"
    send_post_in_topic = "send_post_in_topic"
    create_blog_by_instructor = "create_blog_by_instructor"
    comment_for_instructor_blog = "comment_for_instructor_blog"


class Reward(Base):
    """A points-earning rule, parity of legacy `rewards`.

    For each active `type`, award `score` points when the event fires; amount-
    based types (buy / charge / store-product) scale by `amount / condition`.
    """

    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[RewardType] = mapped_column(
        Enum(RewardType, name="reward_type"), index=True, nullable=False
    )
    score: Mapped[int | None] = mapped_column(Integer)
    condition: Mapped[str | None] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


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
