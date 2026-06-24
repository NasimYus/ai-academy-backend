from datetime import datetime

from pydantic import BaseModel

from app.schemas.course import CourseRead


class FavoriteRead(BaseModel):
    id: int  # favorite row id (use for DELETE /favorites/{id})
    created_at: datetime
    course: CourseRead
