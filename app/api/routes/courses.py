from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.repositories import courses as courses_repo
from app.schemas.common import error_responses
from app.schemas.course import CourseRead

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseRead])
async def list_courses(
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[CourseRead]:
    return await courses_repo.list_published(db, limit=limit, offset=offset)


@router.get(
    "/{slug}",
    response_model=CourseRead,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def get_course(slug: str, db: DbSession) -> CourseRead:
    course = await courses_repo.get_by_slug(db, slug)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course
