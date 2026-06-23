from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.models.course import CourseType
from app.repositories import courses as courses_repo
from app.schemas.common import error_responses
from app.schemas.course import CourseDetail, CourseRead
from app.services.course_presenter import to_brief, to_detail

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseRead])
async def list_courses(
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    cat: int | None = Query(None, description="category id"),
    free: bool | None = Query(None),
    course_type: Annotated[CourseType | None, Query(alias="type")] = None,
    upcoming: bool | None = Query(None),
    downloadable: bool | None = Query(None),
    reward: bool | None = Query(None),
    sort: str | None = Query(None, description="newest|oldest|expensive|cheapest"),
) -> list[CourseRead]:
    courses = await courses_repo.list_courses(
        db,
        category=cat,
        free=free,
        course_type=course_type,
        upcoming=upcoming,
        downloadable=downloadable,
        reward=reward,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return [to_brief(c) for c in courses]


@router.get(
    "/{slug}",
    response_model=CourseDetail,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def get_course(slug: str, db: DbSession) -> CourseDetail:
    course = await courses_repo.get_by_slug(db, slug)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return to_detail(course)
