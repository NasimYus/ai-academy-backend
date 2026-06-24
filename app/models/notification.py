import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationType(str, enum.Enum):
    single = "single"  # to one user_id
    all_users = "all_users"  # broadcast (non-admin)
    students = "students"  # role = user
    instructors = "instructors"  # role = teacher
    organizations = "organizations"  # role = organization


class NotificationSender(str, enum.Enum):
    system = "system"
    admin = "admin"


class Notification(Base):
    """In-app notification, parity of legacy `notifications`.

    Audience is `type`: `single` targets `user_id`; the rest are broadcasts
    resolved against the recipient's role. (legacy `group`/`course_students`
    audiences land with user-groups.)
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sender: Mapped[NotificationSender] = mapped_column(
        Enum(NotificationSender, name="notification_sender"),
        default=NotificationSender.system,
        nullable=False,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NotificationStatus(Base):
    """Per-user read marker, parity of `notifications_status`."""

    __tablename__ = "notifications_status"
    __table_args__ = (
        UniqueConstraint("user_id", "notification_id", name="uq_notification_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
