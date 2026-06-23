from datetime import datetime

from pydantic import BaseModel

from app.schemas.course import CourseRead
from app.schemas.user import UserBrief


class ProviderList(BaseModel):
    """Legacy handleProviders() result: {count, users:[brief]}."""

    count: int
    users: list[UserBrief] = []


class PublicProfile(BaseModel):
    """Public user profile (legacy user->details subset for Phase 2)."""

    id: int
    full_name: str | None
    role_name: str
    avatar: str | None
    cover_img: str | None
    headline: str | None
    bio: str | None
    about: str | None
    created_at: datetime
    courses_count: int = 0
    courses: list[CourseRead] = []
    # NOTE(Phase): cashback_rules, meeting/consultation, rates, badges deferred.
