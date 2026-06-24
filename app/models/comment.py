import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class CommentStatus(str, enum.Enum):
    open = "open"
    replied = "replied"
    new = "new"


class Comment(Base):
    """Comment, parity of legacy polymorphic `comments` table.

    Targets a course (`course_id`, legacy webinar_id) or a blog (`blog_id`);
    exactly one is set. `reply_id` threads one level of replies.
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    blog_id: Mapped[int | None] = mapped_column(
        ForeignKey("blog.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reply_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), index=True
    )
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CommentStatus] = mapped_column(
        Enum(CommentStatus, name="comment_status"), default=CommentStatus.new, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", lazy="raise")
