from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models.enrollment import EnrollmentSource
from app.models.subscription import Subscribe
from app.repositories import courses as courses_repo
from app.repositories import enrollments as enrollments_repo
from app.repositories import orders as orders_repo
from app.repositories import subscriptions as subs_repo
from app.schemas.common import error_responses
from app.schemas.order import OrderRead
from app.schemas.subscription import (
    SubscribeApplyRequest,
    SubscribeList,
    SubscribePlan,
    SubscribeResponse,
)
from app.services import access
from app.services import subscriptions as subs_service
from app.services.order_presenter import order_read

router = APIRouter(prefix="/subscribe", tags=["subscriptions"])


def _plan(s: Subscribe) -> SubscribePlan:
    return SubscribePlan(
        id=s.id,
        title=s.title,
        usable_count=s.usable_count,
        days=s.days,
        price=float(s.price),
        icon=s.icon,
        description=s.description,
    )


@router.get("", response_model=SubscribeList)
async def list_subscriptions(db: DbSession, current_user: OptionalUser) -> SubscribeList:
    """Subscription plans + the user's active subscription (legacy list)."""
    plans = await subs_repo.list_plans(db)
    subscribed = None
    day_of_use = None
    if current_user is not None:
        state = await subs_service.get_active(db, current_user.id)
        if state is not None:
            subscribed = subs_service.to_active_schema(state)
            day_of_use = state.days_used
    return SubscribeList(
        count=len(plans),
        subscribes=[_plan(p) for p in plans],
        subscribed=subscribed,
        day_of_use=day_of_use,
    )


@router.post(
    "/{plan_id}/activate",
    response_model=SubscribeResponse,
    responses=error_responses(status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def activate_subscription(
    plan_id: int, current_user: CurrentUser, db: DbSession
) -> SubscribeResponse:
    """Activate a free plan (paid checkout via webPay is deferred)."""
    plan = await subs_repo.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if float(plan.price) > 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_free")
    await subs_repo.create_user_subscribe(db, user_id=current_user.id, subscribe_id=plan.id)
    return SubscribeResponse(message="subscribed")


@router.post(
    "/{plan_id}/pay",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def pay_subscription(plan_id: int, current_user: CurrentUser, db: DbSession) -> OrderRead:
    """Create a pending order for a paid plan (legacy webPay). Settling it via
    /payments activates the subscription and records a `subscribe` Sale."""
    plan = await subs_repo.get_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    price = float(plan.price)
    if price <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_free")

    order = await orders_repo.create(
        db,
        user_id=current_user.id,
        amount=price,
        total_discount=0,
        total_amount=price,
        items=[{"subscribe_id": plan_id, "amount": price, "total_amount": price}],
    )
    return order_read(order)


@router.post(
    "/apply",
    response_model=SubscribeResponse,
    responses=error_responses(status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def apply_subscription(
    payload: SubscribeApplyRequest, current_user: CurrentUser, db: DbSession
) -> SubscribeResponse:
    """Use the active subscription to unlock a subscribable course (legacy apply)."""
    course = await courses_repo.get_by_id(db, payload.course_id)
    if course is None or course.status.value != "active" or course.private:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if not course.subscribe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_subscribable"
        )
    state = await subs_service.get_active(db, current_user.id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="no_active_subscribe"
        )
    if float(course.price) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="free")
    if await access.has_course_access(db, current_user, course):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="already_purchased"
        )

    await subs_repo.create_use(
        db, user_id=current_user.id, subscribe_id=state.plan.id, course_id=course.id
    )
    await enrollments_repo.create(
        db, user_id=current_user.id, course_id=course.id, source=EnrollmentSource.subscribe
    )
    return SubscribeResponse(message="subscribed")
