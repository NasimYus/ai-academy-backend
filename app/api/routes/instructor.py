from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, require_level
from app.models.category import Category
from app.models.course import Course, CourseStatus, CourseType
from app.models.user import User
from app.repositories import courses as courses_repo
from app.schemas.common import error_responses
from app.schemas.course import CourseDetail, CourseRead
from app.schemas.instructor import CourseCreate, CourseUpdate
from app.services.course_presenter import to_brief, to_detail

router = APIRouter(prefix="/panel", tags=["instructor"])

# Teacher or organization (legacy api.level-access:teacher).
TeacherUser = Annotated[User, Depends(require_level("teacher"))]

_EDITABLE = (
    "title",
    "type",
    "thumbnail",
    "image_cover",
    "description",
    "category_id",
    "duration",
    "start_date",
    "capacity",
    "seo_description",
    "video_demo",
    "video_demo_source",
    "price",
    "organization_price",
    "points",
    "access_days",
    "private",
    "support",
    "downloadable",
    "partner_instructor",
    "subscribe",
)


async def _ensure_category(db: DbSession, category_id: int | None) -> None:
    if category_id is not None and await db.get(Category, category_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="category_not_found"
        )


@router.get("/classes", response_model=list[CourseRead])
async def my_classes(current_user: TeacherUser, db: DbSession) -> list[CourseRead]:
    """The instructor's own courses (legacy WebinarsController@list)."""
    courses = await courses_repo.list_by_creator(db, current_user.id)
    return [to_brief(c) for c in courses]


@router.post(
    "/webinar",
    response_model=CourseDetail,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_course(payload: CourseCreate, current_user: TeacherUser, db: DbSession):
    """Create a course (legacy WebinarsController@storeAll)."""
    await _ensure_category(db, payload.category_id)
    if payload.type == CourseType.webinar and payload.start_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="start_date_required"
        )

    # Draft unless the T&C were accepted and it wasn't explicitly saved as draft.
    course_status = (
        CourseStatus.pending if payload.rules and not payload.draft else CourseStatus.is_draft
    )
    data = payload.model_dump(exclude={"rules", "draft"})
    course = Course(
        **data,
        creator_id=current_user.id,
        teacher_id=current_user.id,
        status=course_status,
        slug=await courses_repo.unique_slug(db, payload.title),
    )
    course = await courses_repo.create_course(db, course)
    return to_detail(course)


@router.get(
    "/webinar/{course_id}/edit",
    response_model=CourseDetail,
    responses=error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
)
async def edit_course(course_id: int, current_user: TeacherUser, db: DbSession) -> CourseDetail:
    course = await courses_repo.get_owned(db, course_id, current_user.id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return to_detail(course)


@router.put(
    "/webinar/{course_id}",
    response_model=CourseDetail,
    responses=error_responses(
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def update_course(
    course_id: int, payload: CourseUpdate, current_user: TeacherUser, db: DbSession
) -> CourseDetail:
    course = await courses_repo.get_owned(db, course_id, current_user.id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes:
        await _ensure_category(db, changes["category_id"])
    changes = {k: v for k, v in changes.items() if k in _EDITABLE}
    course = await courses_repo.update_course(db, course, changes)
    return to_detail(course)


@router.delete(
    "/webinar/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
)
async def delete_course(course_id: int, current_user: TeacherUser, db: DbSession) -> None:
    course = await courses_repo.get_owned(db, course_id, current_user.id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    await courses_repo.delete_course(db, course)
