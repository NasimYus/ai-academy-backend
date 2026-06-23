from fastapi import APIRouter

from app.api.deps import DbSession
from app.repositories import courses as courses_repo
from app.schemas.course import CourseRead
from app.services.course_presenter import to_brief

router = APIRouter(tags=["featured"])


@router.get("/featured-courses", response_model=list[CourseRead])
async def featured_courses(db: DbSession) -> list[CourseRead]:
    courses = await courses_repo.list_featured(db)
    return [to_brief(c) for c in courses]
