"""Content translations (F.4) — parity of legacy Astrotomic `*_translations`.

Each translatable model gets a sidecar table keyed by (entity_id, locale). The
base column on the main table holds the default-locale value; a translation row
overrides it for a given locale. Resolution falls back: requested → default →
base column (see `app/services/i18n.py`).
"""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CategoryTranslation(Base):
    """Localized category fields, parity of `category_translations`."""

    __tablename__ = "category_translations"
    __table_args__ = (
        UniqueConstraint("category_id", "locale", name="uq_category_translation_locale"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    title: Mapped[str | None] = mapped_column(String(64))


class CourseTranslation(Base):
    """Localized course fields, parity of `webinar_translations`."""

    __tablename__ = "course_translations"
    __table_args__ = (UniqueConstraint("course_id", "locale", name="uq_course_translation_locale"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    seo_description: Mapped[str | None] = mapped_column(String(128))
