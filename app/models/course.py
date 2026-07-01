import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.category import Category
from app.models.translation import CourseTranslation
from app.models.user import User


class CourseType(str, enum.Enum):
    """Legacy `webinars.type` enum (webinar = live, course = self-paced)."""

    webinar = "webinar"
    course = "course"
    text_lesson = "text_lesson"


class CourseStatus(str, enum.Enum):
    """Legacy `webinars.status` enum (parity — was draft/published/archived)."""

    active = "active"
    pending = "pending"
    is_draft = "is_draft"
    inactive = "inactive"


class VideoDemoSource(str, enum.Enum):
    upload = "upload"
    youtube = "youtube"
    vimeo = "vimeo"
    external_link = "external_link"


class Course(Base):
    """Course, parity of the legacy `webinars` table (webinar = course).

    Legacy epoch-int columns (`start_date`, `created_at`) are stored as
    `timestamptz` (idiomatic PG, per CLAUDE.md). `title`/`description` are
    translatable in legacy — multilingual content is deferred to F.4.
    """

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    type: Mapped[CourseType] = mapped_column(
        Enum(CourseType, name="course_type"), default=CourseType.course, nullable=False
    )
    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus, name="course_status"), default=CourseStatus.is_draft, nullable=False
    )

    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    creator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )

    locale: Mapped[str | None] = mapped_column(String(8))  # primary content language
    message_for_reviewer: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    seo_description: Mapped[str | None] = mapped_column(String(128))
    thumbnail: Mapped[str | None] = mapped_column(String(512))
    image_cover: Mapped[str | None] = mapped_column(String(512))
    icon: Mapped[str | None] = mapped_column(String(512))
    video_demo: Mapped[str | None] = mapped_column(String(512))
    video_demo_source: Mapped[VideoDemoSource | None] = mapped_column(
        Enum(VideoDemoSource, name="video_demo_source")
    )

    price: Mapped[float] = mapped_column(Numeric(15, 3), default=0, nullable=False)
    organization_price: Mapped[float | None] = mapped_column(Numeric(15, 3))

    capacity: Mapped[int | None] = mapped_column(Integer)
    access_days: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[int | None] = mapped_column(Integer)  # minutes
    points: Mapped[int | None] = mapped_column(Integer)

    support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscribe: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    partner_instructor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    downloadable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    certificate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    forum: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_waitlist: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    only_for_students: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    timezone: Mapped[str | None] = mapped_column(String(64))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    teacher: Mapped[User | None] = relationship("User", foreign_keys=[teacher_id], lazy="raise")
    category: Mapped[Category | None] = relationship("Category", lazy="raise")
    translations: Mapped[list["CourseTranslation"]] = relationship(
        "CourseTranslation", cascade="all, delete-orphan", lazy="raise"
    )
