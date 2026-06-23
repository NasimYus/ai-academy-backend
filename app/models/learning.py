from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CourseLearning(Base):
    """Per-user 'learned' marker for a content item, parity of `course_learning`.

    Polymorphic via nullable item ids (exactly one set). `course_id` is
    denormalized so progress can be queried per course without joins.
    """

    __tablename__ = "course_learning"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_id: Mapped[int | None] = mapped_column(ForeignKey("course_files.id", ondelete="CASCADE"))
    text_lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("text_lessons.id", ondelete="CASCADE")
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("course_sessions.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
