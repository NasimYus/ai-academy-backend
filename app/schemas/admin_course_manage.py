"""Admin course-management list schemas (parity of Admin\\WebinarController@index).
The three sidebar modules — Курсы / Онлайн курсы / Текстовые курсы — share this
shape and differ only by `type`. Live-sessions history is a separate list."""

from datetime import datetime

from pydantic import BaseModel

from app.models.course import CourseStatus, CourseType


class AdminCourseManageRow(BaseModel):
    id: int
    title: str
    type: CourseType
    status: CourseStatus
    category_name: str | None
    teacher_id: int | None
    teacher_name: str | None
    price: float
    is_free: bool
    capacity: int | None
    duration: int | None  # minutes
    sales_count: int
    students_count: int
    income: float
    created_at: datetime
    updated_at: datetime | None


class AdminCourseManageList(BaseModel):
    # headline stats for the module (by type, ignoring the row filters — legacy parity)
    total_courses: int
    total_pending: int
    total_duration: int  # minutes
    total_sales: int
    # pagination of the filtered rows
    page: int
    per_page: int
    total: int
    courses: list[AdminCourseManageRow]


class TeacherOption(BaseModel):
    """Instructor picker option for admin course create (legacy `teachers` list)."""

    id: int
    full_name: str | None


class LiveSessionRow(BaseModel):
    id: int
    course_title: str | None
    session_title: str | None
    session_duration: int | None  # minutes
    start_date: datetime | None
    end_date: datetime | None
    meeting_duration: int | None  # minutes


class LiveSessionList(BaseModel):
    page: int
    per_page: int
    total: int
    sessions: list[LiveSessionRow]
