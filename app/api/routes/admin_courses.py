from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AdminUser, DbSession
from app.models.course import Course, CourseStatus
from app.repositories import courses as courses_repo
from app.schemas.admin_course import AdminCourseList, AdminCourseRead
from app.schemas.common import error_responses

router = APIRouter(prefix="/admin/courses", tags=["admin-courses"])

_ADMIN_ERRORS = error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
_NOT_FOUND = error_responses(
    status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
)


def _read(course: Course) -> AdminCourseRead:
    return AdminCourseRead(
        id=course.id,
        title=course.title,
        slug=course.slug,
        status=course.status,
        type=course.type,
        teacher_id=course.teacher_id,
        price=float(course.price),
        created_at=course.created_at,
    )


@router.get("", response_model=AdminCourseList, responses=_ADMIN_ERRORS)
async def list_courses(
    admin: AdminUser,
    db: DbSession,
    status_filter: Annotated[CourseStatus | None, Query(alias="status")] = None,
) -> AdminCourseList:
    """All courses (optionally by status), newest first, + pending count."""
    courses = await courses_repo.admin_list(db, status_filter)
    pending = await courses_repo.count_by_status(db, CourseStatus.pending)
    return AdminCourseList(
        count=len(courses), pending_count=pending, courses=[_read(c) for c in courses]
    )


async def _set_status(db: DbSession, course_id: int, new_status: CourseStatus) -> AdminCourseRead:
    course = await courses_repo.get_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    course.status = new_status
    await db.commit()
    return _read(course)


@router.post("/{course_id}/approve", response_model=AdminCourseRead, responses=_NOT_FOUND)
async def approve_course(course_id: int, admin: AdminUser, db: DbSession) -> AdminCourseRead:
    """Publish a pending course (legacy approve → active)."""
    return await _set_status(db, course_id, CourseStatus.active)


@router.post("/{course_id}/reject", response_model=AdminCourseRead, responses=_NOT_FOUND)
async def reject_course(course_id: int, admin: AdminUser, db: DbSession) -> AdminCourseRead:
    """Reject a course (legacy reject → inactive)."""
    return await _set_status(db, course_id, CourseStatus.inactive)


@router.post("/{course_id}/unpublish", response_model=AdminCourseRead, responses=_NOT_FOUND)
async def unpublish_course(course_id: int, admin: AdminUser, db: DbSession) -> AdminCourseRead:
    """Send an active course back to moderation (legacy unpublish → pending)."""
    return await _set_status(db, course_id, CourseStatus.pending)
