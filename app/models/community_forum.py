import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class ForumCategoryStatus(str, enum.Enum):
    disabled = "disabled"
    active = "active"


class ForumCategory(Base):
    """A forum category, parity of legacy `forums` (title/description inlined)."""

    __tablename__ = "forums"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("forums.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[int | None] = mapped_column(Integer)  # optional role gating (not enforced yet)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ForumCategoryStatus] = mapped_column(
        Enum(ForumCategoryStatus, name="forum_category_status"),
        default=ForumCategoryStatus.active,
        nullable=False,
    )
    close: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ForumTopic(Base):
    """A discussion topic, parity of legacy `forum_topics`."""

    __tablename__ = "forum_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    forum_id: Mapped[int] = mapped_column(
        ForeignKey("forums.id", ondelete="CASCADE"), index=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cover: Mapped[str | None] = mapped_column(String(512))
    pin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    close: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    creator: Mapped["User | None"] = relationship("User", lazy="raise")
    posts: Mapped[list["ForumTopicPost"]] = relationship(
        "ForumTopicPost", cascade="all, delete-orphan", lazy="raise"
    )


class ForumTopicPost(Base):
    """A post/reply in a topic (nested via parent_id), parity of `forum_topic_posts`."""

    __tablename__ = "forum_topic_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("forum_topics.id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("forum_topic_posts.id", ondelete="SET NULL")
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    attach: Mapped[str | None] = mapped_column(String(512))
    pin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User | None"] = relationship("User", lazy="raise")
