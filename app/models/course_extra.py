import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExtraType(str, enum.Enum):
    """Bullet lists shown on the course page (legacy webinar_extra_descriptions)."""

    learning = "learning"  # "Учебные материалы" / what you will learn
    requirement = "requirement"  # "Требования"


class Faq(Base):
    """Course FAQ item, parity of legacy `faqs`."""

    __tablename__ = "course_faqs"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    locale: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    question: Mapped[str] = mapped_column(String(512), nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CourseExtra(Base):
    """A learning-material or requirement bullet, parity of extra descriptions."""

    __tablename__ = "course_extras"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[ExtraType] = mapped_column(
        Enum(ExtraType, name="course_extra_type"), nullable=False
    )
    locale: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CompanyLogo(Base):
    """A company/partner logo shown on the course page (legacy company logos)."""

    __tablename__ = "course_company_logos"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    image: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
