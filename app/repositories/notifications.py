from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationStatus, NotificationType
from app.models.user import User

# Which broadcast type each role sees (legacy User@getUnReadNotifications).
_ROLE_BROADCAST = {
    "user": NotificationType.students,
    "teacher": NotificationType.instructors,
    "organization": NotificationType.organizations,
}


def _audience(user: User):
    """Filter selecting notifications addressed to the given user (legacy `all()`).

    `single` → personal (user_id == me); `all_users` → broadcast to everyone;
    plus the one role bucket matching the user's role. Admins skip `all_users`
    (legacy quirk). `group`/`course_students` audiences are not migrated yet.
    """
    clauses = [
        and_(Notification.type == NotificationType.single, Notification.user_id == user.id),
    ]
    if user.role_name != "admin":
        clauses.append(
            and_(
                Notification.type == NotificationType.all_users,
                Notification.user_id.is_(None),
            )
        )
    bucket = _ROLE_BROADCAST.get(user.role_name)
    if bucket is not None:
        clauses.append(and_(Notification.type == bucket, Notification.user_id.is_(None)))
    return or_(*clauses)


async def list_for_user(db: AsyncSession, user: User) -> list[tuple[Notification, bool]]:
    """All notifications for the user (newest first), each paired with read flag.

    Read status is per-user: a row in `notifications_status` for (me, notification).
    """
    seen_sub = select(NotificationStatus.notification_id).where(
        NotificationStatus.user_id == user.id
    )
    result = await db.execute(
        select(Notification, Notification.id.in_(seen_sub))
        .where(_audience(user))
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )
    return [(n, bool(read)) for n, read in result.all()]


async def get_for_user(db: AsyncSession, user: User, notification_id: int) -> Notification | None:
    """A single notification visible to the user, or None."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, _audience(user))
    )
    return result.scalar_one_or_none()


async def is_seen(db: AsyncSession, *, user_id: int, notification_id: int) -> bool:
    result = await db.execute(
        select(NotificationStatus.id).where(
            NotificationStatus.user_id == user_id,
            NotificationStatus.notification_id == notification_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def mark_seen(db: AsyncSession, *, user_id: int, notification_id: int) -> None:
    db.add(NotificationStatus(user_id=user_id, notification_id=notification_id))
    await db.commit()
