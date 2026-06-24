import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NoteTargetType(str, enum.Enum):
    session = "session"
    file = "file"
    quiz = "quiz"
    text_lesson = "text_lesson"
    assignment = "assignment"


class CoursePersonalNote(Base):
    """Per-user note attached to a content item, parity of `course_personal_notes`.

    Legacy uses a polymorphic `targetable_type`/`targetable_id` (PHP class strings);
    we store an idiomatic `target_type` enum + `target_id`. One note per
    (user, course, target) — enforced for the legacy updateOrCreate semantics.
    """

    __tablename__ = "course_personal_notes"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "course_id", "target_type", "target_id", name="uq_personal_note_target"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_type: Mapped[NoteTargetType] = mapped_column(
        Enum(NoteTargetType, name="note_target_type"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    attachment: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
