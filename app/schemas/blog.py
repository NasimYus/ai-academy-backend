from datetime import datetime

from pydantic import BaseModel

from app.schemas.review import CommentRead
from app.schemas.user import UserBrief


class BlogBrief(BaseModel):
    id: int
    title: str
    image: str | None
    description: str | None  # truncated to ~160 chars (legacy)
    created_at: datetime
    author: UserBrief | None
    comment_count: int
    category: str | None


class BlogDetail(BlogBrief):
    content: str
    comments: list[CommentRead]


class BlogList(BaseModel):
    count: int
    blogs: list[BlogBrief]


class BlogShow(BaseModel):
    blog: BlogDetail


class BlogCategoryRead(BaseModel):
    id: int
    title: str
    slug: str


class BlogCommentCreate(BaseModel):
    comment: str
    reply_id: int | None = None
