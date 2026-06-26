from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AdminUser, DbSession
from app.models.review import CourseReview, ReviewStatus
from app.repositories import reviews as reviews_repo
from app.schemas.common import error_responses
from app.schemas.review import AdminReviewList, AdminReviewRead
from app.schemas.user import UserBrief

router = APIRouter(prefix="/admin/reviews", tags=["admin-reviews"])

_ADMIN_ERRORS = error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
_NOT_FOUND = error_responses(
    status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
)


def _read(review: CourseReview) -> AdminReviewRead:
    return AdminReviewRead(
        id=review.id,
        course_id=review.course_id,
        user=UserBrief.model_validate(review.user) if review.user else None,
        content_quality=review.content_quality,
        instructor_skills=review.instructor_skills,
        purchase_worth=review.purchase_worth,
        support_quality=review.support_quality,
        rates=review.rates,
        description=review.description,
        status=review.status,
        created_at=review.created_at,
    )


@router.get("", response_model=AdminReviewList, responses=_ADMIN_ERRORS)
async def list_reviews(
    admin: AdminUser,
    db: DbSession,
    status_filter: Annotated[ReviewStatus | None, Query(alias="status")] = ReviewStatus.pending,
) -> AdminReviewList:
    """Reviews for moderation (defaults to the pending queue)."""
    reviews = await reviews_repo.list_by_status(db, status_filter)
    return AdminReviewList(count=len(reviews), reviews=[_read(r) for r in reviews])


@router.post("/{review_id}/approve", response_model=AdminReviewRead, responses=_NOT_FOUND)
async def approve_review(review_id: int, admin: AdminUser, db: DbSession) -> AdminReviewRead:
    """Publish a pending review (legacy publish → active)."""
    review = await reviews_repo.get_by_id(db, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    review.status = ReviewStatus.active
    await db.commit()
    return _read(review)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_NOT_FOUND)
async def reject_review(review_id: int, admin: AdminUser, db: DbSession) -> None:
    """Reject (delete) a review (legacy destroy)."""
    review = await reviews_repo.get_by_id(db, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    await reviews_repo.delete_review(db, review)
