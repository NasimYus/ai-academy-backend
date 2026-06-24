import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SupportStatus(str, enum.Enum):
    open = "open"
    close = "close"
    replied = "replied"
    supporter_replied = "supporter_replied"


class SupportDepartment(Base):
    """Platform support department (legacy `support_departments`).

    Legacy stores `title` via a translations table; we keep it inline (tiny
    admin-seeded list, `details` only ever exposes id+title). NOTE(i18n).
    """

    __tablename__ = "support_departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    icon: Mapped[str | None] = mapped_column(String(255))
    color: Mapped[str | None] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Support(Base):
    """A support ticket (legacy `supports`).

    `course_support` tickets carry `course_id` (legacy `webinar_id`);
    `platform_support` tickets carry `department_id`.
    """

    __tablename__ = "supports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("support_departments.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[SupportStatus] = mapped_column(
        Enum(SupportStatus, name="support_status"),
        default=SupportStatus.open,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id], lazy="raise")  # noqa: F821
    course: Mapped["Course | None"] = relationship(lazy="raise")  # noqa: F821
    department: Mapped["SupportDepartment | None"] = relationship(lazy="raise")
    conversations: Mapped[list["SupportConversation"]] = relationship(
        back_populates="support",
        lazy="raise",
        order_by="SupportConversation.id",
        cascade="all, delete-orphan",
    )


class SupportConversation(Base):
    """A message within a support ticket (legacy `support_conversations`).

    `sender_id` is the message author; `supporter_id` is the admin/support
    agent (unset in the user-facing flow).
    """

    __tablename__ = "support_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    support_id: Mapped[int] = mapped_column(
        ForeignKey("supports.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    supporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    attach: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    support: Mapped["Support"] = relationship(back_populates="conversations", lazy="raise")
    sender: Mapped["User | None"] = relationship(  # noqa: F821
        foreign_keys=[sender_id], lazy="raise"
    )
    supporter: Mapped["User | None"] = relationship(  # noqa: F821
        foreign_keys=[supporter_id], lazy="raise"
    )
