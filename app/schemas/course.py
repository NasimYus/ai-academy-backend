from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.course import CourseStatus


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    description: str | None
    thumbnail: str | None
    price: float
    status: CourseStatus
    teacher_id: int | None
    created_at: datetime
