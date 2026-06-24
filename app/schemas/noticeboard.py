from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserBrief


class NoticeboardRead(BaseModel):
    id: int
    title: str
    message: str
    color: str
    icon: str
    created_at: datetime
    creator: UserBrief | None = None
