import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class AssignmentStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class AssignmentHistoryStatus(str, enum.Enum):
    """Legacy WebinarAssignmentHistory::$assignmentHistoryStatus."""

    pending = "pending"
    passed = "passed"
    not_passed = "not_passed"
    not_submitted = "not_submitted"


class Assignment(Base):
    """Course assignment, parity of `webinar_assignments` (webinar = course)."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    grade: Mapped[int | None] = mapped_column(Integer)  # total mark
    pass_grade: Mapped[int | None] = mapped_column(Integer)
    deadline: Mapped[int | None] = mapped_column(Integer)  # days from access start
    attempts: Mapped[int | None] = mapped_column(Integer)  # null = unlimited
    check_previous_parts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_after_day: Mapped[int | None] = mapped_column(Integer)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status"),
        default=AssignmentStatus.active,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # NOTE(6.x): instructor-uploaded attachment files deferred to Phase 6.


class AssignmentHistory(Base):
    """A student's submission thread for an assignment (`webinar_assignment_history`)."""

    __tablename__ = "assignment_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    instructor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    grade: Mapped[int | None] = mapped_column(Integer)  # set by instructor (Phase 6)
    status: Mapped[AssignmentHistoryStatus] = mapped_column(
        Enum(AssignmentHistoryStatus, name="assignment_history_status"),
        default=AssignmentHistoryStatus.not_submitted,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assignment: Mapped[Assignment] = relationship("Assignment", lazy="raise")
    student: Mapped[User] = relationship("User", foreign_keys=[student_id], lazy="raise")
    instructor: Mapped[User] = relationship("User", foreign_keys=[instructor_id], lazy="raise")


class AssignmentHistoryMessage(Base):
    """A message/submission in a thread (`webinar_assignment_history_messages`)."""

    __tablename__ = "assignment_history_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_history_id: Mapped[int] = mapped_column(
        ForeignKey("assignment_history.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    file_title: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sender: Mapped[User] = relationship("User", lazy="raise")
