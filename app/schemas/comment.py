from datetime import datetime

from pydantic import BaseModel


class MyCommentRead(BaseModel):
    """A student's own comment for the panel `my-comments` list."""

    id: int
    comment: str | None = None
    status: str
    course_id: int | None = None
    blog_id: int | None = None
    created_at: datetime
