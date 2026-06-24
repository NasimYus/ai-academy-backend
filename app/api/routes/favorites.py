from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrencyCtx, CurrentUser, DbSession, Locale
from app.core.config import settings
from app.models.course import CourseStatus
from app.repositories import courses as courses_repo
from app.repositories import favorites as favorites_repo
from app.schemas.common import error_responses
from app.schemas.favorite import FavoriteRead
from app.services.course_presenter import to_brief

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteRead], responses=error_responses(401))
async def list_favorites(
    current_user: CurrentUser, db: DbSession, locale: Locale, currency: CurrencyCtx
) -> list[FavoriteRead]:
    """The user's favorited courses (legacy FavoritesController@list)."""
    favorites = await favorites_repo.list_for_user(db, current_user.id)
    return [
        FavoriteRead(
            id=f.id,
            created_at=f.created_at,
            course=to_brief(f.course, locale, settings.default_locale, currency),
        )
        for f in favorites
        if f.course is not None
    ]


@router.post(
    "/toggle/{course_id}",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def toggle_favorite(
    course_id: int, current_user: CurrentUser, db: DbSession
) -> dict[str, str]:
    """Toggle a course in favorites (legacy FavoritesController@toggle)."""
    course = await courses_repo.get_by_id(db, course_id)
    if course is None or course.status != CourseStatus.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    existing = await favorites_repo.get(db, user_id=current_user.id, course_id=course.id)
    if existing is None:
        await favorites_repo.add(db, user_id=current_user.id, course_id=course.id)
        return {"status": "favored"}
    await favorites_repo.remove(db, existing)
    return {"status": "unfavored"}


@router.delete(
    "/{favorite_id}",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def delete_favorite(
    favorite_id: int, current_user: CurrentUser, db: DbSession
) -> dict[str, str]:
    """Remove a favorite by id (legacy FavoritesController@destroy, owner-scoped)."""
    favorite = await favorites_repo.get_owned(db, favorite_id, current_user.id)
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    await favorites_repo.remove(db, favorite)
    return {"status": "deleted"}
