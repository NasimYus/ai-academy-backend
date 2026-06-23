import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    active = "active"


class CourseReview(Base):
    """Course review, parity of legacy `webinar_reviews`."""

    __tablename__ = "course_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_quality: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    instructor_skills: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    purchase_worth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    support_quality: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # overall
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"), default=ReviewStatus.pending, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", lazy="raise")
