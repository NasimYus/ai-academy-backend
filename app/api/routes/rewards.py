from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.reward import RewardStatus
from app.repositories import courses as courses_repo
from app.repositories import enrollments as enrollments_repo
from app.repositories import rewards as rewards_repo
from app.schemas.common import error_responses
from app.schemas.course import CourseRead
from app.schemas.reward import RedeemResponse, RewardsOverview
from app.services import access
from app.services import rewards as rewards_service
from app.services.course_presenter import to_brief

router = APIRouter(prefix="/rewards", tags=["rewards"])


@router.get(
    "",
    response_model=RewardsOverview,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def rewards_overview(current_user: CurrentUser, db: DbSession) -> RewardsOverview:
    """Points overview + history + leaderboard (legacy RewardsController@index)."""
    if not rewards_service.enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rewards_disabled")
    return await rewards_service.build_overview(db, current_user)


@router.get("/reward-courses", response_model=list[CourseRead])
async def reward_courses(db: DbSession) -> list[CourseRead]:
    """Active courses buyable with points (legacy RewardsController@courses — ungated)."""
    courses = await courses_repo.with_reward_points(db)
    return [to_brief(c) for c in courses]


@router.post(
    "/exchange",
    response_model=RedeemResponse,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def exchange(current_user: CurrentUser, db: DbSession) -> RedeemResponse:
    """Exchange points to wallet (legacy RewardsController@exchange)."""
    if not rewards_service.enabled():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="rewards_disabled")

    pts = await rewards_repo.points(db, current_user.id)
    available = pts["available"]
    if available > 0 and rewards_service.settings.rewards_exchangeable:
        await rewards_repo.create_entry(
            db,
            user_id=current_user.id,
            score=available,
            type="withdraw",
            status=RewardStatus.deduction,
        )
        # NOTE(wallet): crediting the user's wallet (legacy Accounting) lands with
        # the wallet/charge subsystem; the points deduction is recorded here.
    return RedeemResponse(message="exchanged")


@router.post(
    "/webinar/{course_id}/apply",
    response_model=RedeemResponse,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def buy_with_points(
    course_id: int, current_user: CurrentUser, db: DbSession
) -> RedeemResponse:
    """Redeem points for a course (legacy RewardsController@buyWithPoint)."""
    course = await courses_repo.get_by_id(db, course_id)
    if course is None or course.status.value != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if not course.points:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="no_points")
    if float(course.price) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="free")
    if await access.has_course_access(db, current_user, course):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="already_purchased"
        )

    available = (await rewards_repo.points(db, current_user.id))["available"]
    if available < course.points:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="no_enough_points"
        )

    await enrollments_repo.create(
        db,
        user_id=current_user.id,
        course_id=course.id,
        source=enrollments_repo.EnrollmentSource.reward,
    )
    await rewards_repo.create_entry(
        db,
        user_id=current_user.id,
        score=course.points,
        type="withdraw",
        status=RewardStatus.deduction,
        item_id=course.id,
    )
    return RedeemResponse(message="paid")
