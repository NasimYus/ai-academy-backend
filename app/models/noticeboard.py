import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class NoticeboardColor(str, enum.Enum):
    warning = "warning"
    danger = "danger"
    neutral = "neutral"
    info = "info"
    success = "success"


class CourseNoticeboard(Base):
    """Course announcement, parity of legacy `course_noticeboards`."""

    __tablename__ = "course_noticeboards"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    color: Mapped[NoticeboardColor] = mapped_column(
        Enum(NoticeboardColor, name="noticeboard_color"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    creator: Mapped["User | None"] = relationship("User", lazy="raise")
