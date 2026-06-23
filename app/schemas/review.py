from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserBrief


class ReviewRead(BaseModel):
    id: int
    user: UserBrief | None = None
    content_quality: int
    instructor_skills: int
    purchase_worth: int
    support_quality: int
    rates: int
    description: str | None
    created_at: datetime


class CommentRead(BaseModel):
    id: int
    user: UserBrief | None = None
    comment: str | None
    created_at: datetime
    replies: list["CommentRead"] = []
