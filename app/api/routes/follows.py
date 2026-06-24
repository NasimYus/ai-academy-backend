from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.repositories import follows as follows_repo
from app.repositories import users as users_repo
from app.schemas.common import error_responses
from app.schemas.user import UserBrief

router = APIRouter(tags=["follows"])


class FollowToggle(BaseModel):
    status: bool  # true = follow, false = unfollow


@router.post(
    "/users/{user_id}/follow",
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND
    ),
)
async def follow_toggle(
    user_id: int, payload: FollowToggle, current_user: CurrentUser, db: DbSession
) -> dict[str, str]:
    """Follow/unfollow a user (legacy UsersController@followToggle)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot_follow_self")
    target = await users_repo.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = await follows_repo.get(db, follower_id=current_user.id, user_id=user_id)
    if payload.status:
        if existing is None:
            await follows_repo.add(db, follower_id=current_user.id, user_id=user_id)
        return {"status": "followed"}
    if existing is not None:
        await follows_repo.remove(db, existing)
    return {"status": "unfollowed"}


@router.get(
    "/panel/following",
    response_model=list[UserBrief],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def my_following(current_user: CurrentUser, db: DbSession) -> list[UserBrief]:
    """Users the current user follows."""
    users = await follows_repo.following(db, current_user.id)
    return [UserBrief.model_validate(u) for u in users]
