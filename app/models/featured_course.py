import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.course import Course


class FeaturedPage(str, enum.Enum):
    categories = "categories"
    home = "home"
    home_categories = "home_categories"


class FeaturedStatus(str, enum.Enum):
    publish = "publish"
    pending = "pending"


class FeaturedCourse(Base):
    """Featured course slot, parity of the legacy `feature_webinars` table."""

    __tablename__ = "featured_courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    page: Mapped[FeaturedPage] = mapped_column(Enum(FeaturedPage, name="featured_page"))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[FeaturedStatus] = mapped_column(
        Enum(FeaturedStatus, name="featured_status"), default=FeaturedStatus.pending, nullable=False
    )
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    course: Mapped[Course] = relationship("Course", lazy="raise")
