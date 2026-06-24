import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BlogStatus(str, enum.Enum):
    pending = "pending"
    publish = "publish"


class BlogCategory(Base):
    """Blog category (legacy `blog_categories`).

    Legacy localizes `title` via translations; we keep it inline (small,
    admin-seeded). NOTE(i18n).
    """

    __tablename__ = "blog_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)


class Blog(Base):
    """A blog post (legacy `blog`).

    Title/description/content are localized via translations in legacy; kept
    inline here (translations deferred). NOTE(i18n).
    """

    __tablename__ = "blog"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("blog_categories.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    image: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enable_comment: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[BlogStatus] = mapped_column(
        Enum(BlogStatus, name="blog_status"), default=BlogStatus.pending, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    author: Mapped["User"] = relationship(lazy="raise")  # noqa: F821
    category: Mapped["BlogCategory | None"] = relationship(lazy="raise")
