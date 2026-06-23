from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.models.role import Role
from app.repositories import courses as courses_repo
from app.repositories import users as users_repo
from app.schemas.search import (
    OrganizationsGroup,
    SearchResults,
    TeachersGroup,
    UsersGroup,
    WebinarsGroup,
)
from app.schemas.user import UserBrief
from app.services.course_presenter import to_brief

router = APIRouter(tags=["search"])

_MIN_LEN = 3  # legacy: searches shorter than 3 chars return empty groups


@router.get("/search", response_model=SearchResults)
async def search(db: DbSession, search: str | None = Query(None)) -> SearchResults:
    if not search or len(search) < _MIN_LEN:
        return SearchResults()

    courses = await courses_repo.search_by_title(db, search)
    users = await users_repo.search(db, search)

    webinars = [to_brief(c) for c in courses]
    user_briefs = [UserBrief.model_validate(u) for u in users]
    teachers = [u for u in user_briefs if u.role_name == Role.TEACHER]
    organizations = [u for u in user_briefs if u.role_name == Role.ORGANIZATION]

    return SearchResults(
        webinars=WebinarsGroup(webinars=webinars, count=len(webinars)),
        users=UsersGroup(users=user_briefs, count=len(user_briefs)),
        teachers=TeachersGroup(teachers=teachers, count=len(teachers)),
        organizations=OrganizationsGroup(organizations=organizations, count=len(organizations)),
    )
