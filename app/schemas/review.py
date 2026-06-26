from datetime import datetime

from pydantic import BaseModel, Field

from app.models.review import ReviewStatus
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


class ReviewCreate(BaseModel):
    content_quality: int = Field(ge=1, le=5)
    instructor_skills: int = Field(ge=1, le=5)
    purchase_worth: int = Field(ge=1, le=5)
    support_quality: int = Field(ge=1, le=5)
    description: str | None = None


class AdminReviewRead(ReviewRead):
    course_id: int
    status: ReviewStatus


class AdminReviewList(BaseModel):
    count: int
    reviews: list[AdminReviewRead]


class CommentRead(BaseModel):
    id: int
    user: UserBrief | None = None
    comment: str | None
    created_at: datetime
    replies: list["CommentRead"] = []
