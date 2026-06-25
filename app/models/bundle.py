import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BundleStatus(str, enum.Enum):
    active = "active"
    pending = "pending"
    is_draft = "is_draft"
    inactive = "inactive"


class Bundle(Base):
    """A bundle of courses (legacy `bundles`).

    Title/description localized via translations in legacy; kept inline here
    (translations deferred). NOTE(i18n).
    """

    __tablename__ = "bundles"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    thumbnail: Mapped[str | None] = mapped_column(String(512))
    image_cover: Mapped[str | None] = mapped_column(String(512))
    price: Mapped[float | None] = mapped_column()
    points: Mapped[int | None] = mapped_column(Integer)
    subscribe: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_days: Mapped[int | None] = mapped_column(Integer)
    message_for_reviewer: Mapped[str | None] = mapped_column(Text)
    status: Mapped[BundleStatus] = mapped_column(
        Enum(BundleStatus, name="bundle_status"), default=BundleStatus.pending, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    category: Mapped["Category | None"] = relationship(lazy="raise")  # noqa: F821
    webinars: Mapped[list["BundleWebinar"]] = relationship(
        back_populates="bundle", lazy="raise", cascade="all, delete-orphan"
    )


class BundleWebinar(Base):
    """A course in a bundle (legacy `bundle_webinars`, webinar_id → course_id)."""

    __tablename__ = "bundle_webinars"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    bundle_id: Mapped[int] = mapped_column(
        ForeignKey("bundles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order: Mapped[int | None] = mapped_column(Integer)

    bundle: Mapped["Bundle"] = relationship(back_populates="webinars", lazy="raise")
    course: Mapped["Course"] = relationship(lazy="raise")  # noqa: F821
