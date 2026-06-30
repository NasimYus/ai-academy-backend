import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class BecomeInstructorStatus(str, enum.Enum):
    pending = "pending"
    accept = "accept"
    reject = "reject"


class BecomeInstructor(Base):
    """A student's request to become an instructor/organization, parity of legacy
    `become_instructors`. Admin approval flips the user's role.

    NOTE(Phase): legacy also collects bank details / identity scan / certificate
    uploads and an optional registration package — those subsystems aren't
    migrated, so the request carries role + occupations + description only.
    """

    __tablename__ = "become_instructors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False, unique=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # teacher | organization
    description: Mapped[str | None] = mapped_column(Text)
    occupations: Mapped[list[int] | None] = mapped_column(JSON)  # category ids
    status: Mapped[BecomeInstructorStatus] = mapped_column(
        Enum(BecomeInstructorStatus, name="become_instructor_status"),
        default=BecomeInstructorStatus.pending,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(lazy="raise")
