from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.enrollment import EnrollmentSource
from app.repositories import courses as courses_repo
from app.repositories import enrollments as enrollments_repo
from app.schemas.common import error_responses
from app.schemas.course import CourseRead
from app.services.course_presenter import to_brief

router = APIRouter(prefix="/panel", tags=["enrollment"])


@router.get(
    "/my-courses",
    response_model=list[CourseRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def my_courses(current_user: CurrentUser, db: DbSession) -> list[CourseRead]:
    """Courses the user has access to (enrolled / purchased)."""
    courses = await enrollments_repo.list_courses_for_user(db, current_user.id)
    return [to_brief(c) for c in courses]


@router.post(
    "/courses/{course_id}/free",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST
    ),
)
async def enroll_free(course_id: int, current_user: CurrentUser, db: DbSession) -> dict[str, str]:
    """Legacy WebinarsController@free: enroll into a free course (amount-0 sale)."""
    course = await courses_repo.get_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if course.price and float(course.price) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="not_free")
    if not await enrollments_repo.exists(db, user_id=current_user.id, course_id=course.id):
        await enrollments_repo.create(
            db, user_id=current_user.id, course_id=course.id, source=EnrollmentSource.free
        )
    return {"status": "enrolled"}
