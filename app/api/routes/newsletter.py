from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, OptionalUser
from app.models.reward import RewardType
from app.repositories import newsletter as newsletter_repo
from app.schemas.common import error_responses
from app.schemas.newsletter import NewsletterRequest, NewsletterResponse
from app.services import rewards as rewards_service

router = APIRouter(tags=["newsletter"])


@router.post(
    "/newsletter",
    response_model=NewsletterResponse,
    responses=error_responses(status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def make_newsletter(
    payload: NewsletterRequest, db: DbSession, current_user: OptionalUser
) -> NewsletterResponse:
    """Subscribe an email to the newsletter (legacy UserController@makeNewsletter)."""
    email = payload.email
    if await newsletter_repo.exists_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="already_subscribed"
        )

    user_id = None
    # Link + flag only when the auth user subscribes with their own email (legacy).
    if current_user is not None and current_user.email == email:
        user_id = current_user.id
        current_user.newsletter = True

    await newsletter_repo.create(db, email=email, user_id=user_id)
    # Newsletter reward (only for an authenticated own-email subscribe; once).
    if user_id is not None:
        await rewards_service.award_for(
            db, user_id=user_id, reward_type=RewardType.newsletters, check_duplicate=True
        )
    return NewsletterResponse(message="subscribed_newsletter")
