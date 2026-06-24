from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.repositories import notifications as notif_repo
from app.schemas.common import error_responses
from app.schemas.notification import NotificationList, NotificationRead

router = APIRouter(tags=["notifications"])


@router.get(
    "/notifications",
    response_model=NotificationList,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[Literal["all", "read", "unread"], Query(alias="status")] = "all",
) -> NotificationList:
    """List the user's notifications (legacy NotificationsController@list).

    `status=unread` keeps only unseen, `read` only seen, anything else returns all.
    """
    rows = await notif_repo.list_for_user(db, current_user)
    if status_filter == "unread":
        rows = [(n, read) for n, read in rows if not read]
    elif status_filter == "read":
        rows = [(n, read) for n, read in rows if read]
    items = [
        NotificationRead(
            id=n.id,
            title=n.title,
            message=n.message,
            type=n.type,
            status="read" if read else "unread",
            created_at=n.created_at,
        )
        for n, read in rows
    ]
    return NotificationList(count=len(items), notifications=items)


@router.post(
    "/notifications/{notification_id}/seen",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def mark_notification_seen(
    notification_id: int, current_user: CurrentUser, db: DbSession
) -> dict[str, str]:
    """Mark a notification as read (legacy NotificationsController@seen)."""
    notification = await notif_repo.get_for_user(db, current_user, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if await notif_repo.is_seen(db, user_id=current_user.id, notification_id=notification_id):
        return {"status": "already_seen"}
    await notif_repo.mark_seen(db, user_id=current_user.id, notification_id=notification_id)
    return {"status": "seen"}
