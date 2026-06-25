from datetime import datetime

from pydantic import BaseModel

from app.models.course import CourseStatus, CourseType


class AdminCourseRead(BaseModel):
    id: int
    title: str
    slug: str
    status: CourseStatus
    type: CourseType
    teacher_id: int | None
    price: float
    created_at: datetime


class AdminCourseList(BaseModel):
    count: int
    pending_count: int
    courses: list[AdminCourseRead]
