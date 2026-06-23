from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.models.role import Role
from app.repositories import courses as courses_repo
from app.repositories import users as users_repo
from app.schemas.common import error_responses
from app.schemas.provider import ProviderList, PublicProfile
from app.schemas.user import UserBrief
from app.services.course_presenter import to_brief

router = APIRouter(tags=["providers"])


async def _providers(db: DbSession, roles: list[str], search: str | None, sort: str | None):
    users = await users_repo.list_providers(db, roles, search=search, sort=sort)
    briefs = [UserBrief.model_validate(u) for u in users]
    return ProviderList(count=len(briefs), users=briefs)


@router.get("/providers/instructors", response_model=ProviderList)
async def instructors(
    db: DbSession, search: str | None = Query(None), sort: str | None = Query(None)
) -> ProviderList:
    return await _providers(db, [Role.TEACHER], search, sort)


@router.get("/providers/organizations", response_model=ProviderList)
async def organizations(
    db: DbSession, search: str | None = Query(None), sort: str | None = Query(None)
) -> ProviderList:
    return await _providers(db, [Role.ORGANIZATION], search, sort)


@router.get("/providers/consultations", response_model=ProviderList)
async def consultations(db: DbSession) -> ProviderList:
    # NOTE(Phase 7): consultations require the meetings subsystem (not ported);
    # empty on a clean install, mirroring legacy with no meetings.
    return ProviderList(count=0, users=[])


@router.get(
    "/users/{user_id}/profile",
    response_model=PublicProfile,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def public_profile(user_id: int, db: DbSession) -> PublicProfile:
    user = await users_repo.get_public_profile(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    courses = await courses_repo.list_by_teacher(db, user.id)
    briefs = [to_brief(c) for c in courses]
    return PublicProfile(
        id=user.id,
        full_name=user.full_name,
        role_name=user.role_name,
        avatar=user.avatar,
        cover_img=user.cover_img,
        headline=user.headline,
        bio=user.bio,
        about=user.about,
        created_at=user.created_at,
        courses_count=len(briefs),
        courses=briefs,
    )
