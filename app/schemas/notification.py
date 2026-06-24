from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.notification import NotificationType


class NotificationRead(BaseModel):
    id: int
    title: str
    message: str
    type: NotificationType
    status: Literal["read", "unread"]
    created_at: datetime


class NotificationList(BaseModel):
    count: int
    notifications: list[NotificationRead]
