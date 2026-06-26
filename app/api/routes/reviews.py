from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.models.review import CourseReview, ReviewStatus
from app.repositories import courses as courses_repo
from app.repositories import reviews as reviews_repo
from app.schemas.common import error_responses
from app.schemas.review import ReviewCreate, ReviewRead
from app.schemas.user import UserBrief
from app.services import access

router = APIRouter(tags=["reviews"])


@router.post(
    "/courses/{course_id}/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_review(
    course_id: int, payload: ReviewCreate, current_user: CurrentUser, db: DbSession
) -> ReviewRead:
    """Submit a course review (legacy WebinarReviewController@store).

    Requires the buyer to own the course; one review per user. Published
    immediately when `direct_publication_of_reviews` is on, else `pending`."""
    course = await courses_repo.get_by_id(db, course_id)
    if course is None or course.status.value != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not await access.has_course_access(db, current_user, course):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_bought")
    if await reviews_repo.get_user_review(db, course_id, current_user.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="duplicate_review"
        )

    rates = (
        payload.content_quality
        + payload.instructor_skills
        + payload.purchase_worth
        + payload.support_quality
    )
    review = CourseReview(
        course_id=course_id,
        user_id=current_user.id,
        content_quality=payload.content_quality,
        instructor_skills=payload.instructor_skills,
        purchase_worth=payload.purchase_worth,
        support_quality=payload.support_quality,
        rates=rates,
        description=payload.description,
        status=(
            ReviewStatus.active if settings.direct_publication_of_reviews else ReviewStatus.pending
        ),
    )
    review = await reviews_repo.create_review(db, review)
    return ReviewRead(
        id=review.id,
        user=UserBrief.model_validate(current_user),
        content_quality=review.content_quality,
        instructor_skills=review.instructor_skills,
        purchase_worth=review.purchase_worth,
        support_quality=review.support_quality,
        rates=review.rates,
        description=review.description,
        created_at=review.created_at,
    )
