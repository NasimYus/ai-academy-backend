import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EnrollmentSource(str, enum.Enum):
    """How access was granted. Paid sources are wired in Phase 4."""

    free = "free"
    purchase = "purchase"
    subscribe = "subscribe"
    gift = "gift"
    bundle = "bundle"


class Enrollment(Base):
    """Grants a user access to a course's content.

    In legacy, access is derived from `Sale` rows (incl. the amount-0 'free'
    enrollment). We model it explicitly; Phase 4 will create enrollments on
    successful purchase/subscription.
    """

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollment_user_course"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[EnrollmentSource] = mapped_column(
        Enum(EnrollmentSource, name="enrollment_source"),
        default=EnrollmentSource.free,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
