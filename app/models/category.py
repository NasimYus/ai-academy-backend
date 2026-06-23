from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Category(Base):
    """Course category, parity of the legacy `categories` table.

    Legacy `title` is translatable (category_translations); multilingual titles
    are deferred to F.4 — for now a single `title` column is used.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, index=True)  # self-ref (logical)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    icon: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(255))
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TrendCategory(Base):
    """Trending category, parity of the legacy `trend_categories` table."""

    __tablename__ = "trend_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    icon: Mapped[str | None] = mapped_column(String(255))
    color: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
