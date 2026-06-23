from pydantic import BaseModel

from app.schemas.course import CourseRead
from app.schemas.user import UserBrief


class WebinarsGroup(BaseModel):
    webinars: list[CourseRead] = []
    count: int = 0


class UsersGroup(BaseModel):
    users: list[UserBrief] = []
    count: int = 0


class TeachersGroup(BaseModel):
    teachers: list[UserBrief] = []
    count: int = 0


class OrganizationsGroup(BaseModel):
    organizations: list[UserBrief] = []
    count: int = 0


class SearchResults(BaseModel):
    """Legacy SearchController shape (multi-entity global search)."""

    webinars: WebinarsGroup = WebinarsGroup()
    users: UsersGroup = UsersGroup()
    teachers: TeachersGroup = TeachersGroup()
    organizations: OrganizationsGroup = OrganizationsGroup()
