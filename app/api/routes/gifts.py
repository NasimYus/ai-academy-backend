from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.enrollment import EnrollmentSource
from app.models.gift import Gift, GiftStatus
from app.repositories import bundles as bundles_repo
from app.repositories import courses as courses_repo
from app.repositories import enrollments as enrollments_repo
from app.repositories import gifts as gifts_repo
from app.repositories import orders as orders_repo
from app.schemas.common import error_responses
from app.schemas.gift import GiftActionResponse, GiftCreate, GiftItemType, GiftRead
from app.schemas.order import OrderRead
from app.services.order_presenter import order_read

router = APIRouter(tags=["gifts"])


async def _resolve_item(db: DbSession, item_type: GiftItemType, item_id: int):
    """Return (title, price, fields) for the gifted course/bundle, or None."""
    if item_type == GiftItemType.course:
        course = await courses_repo.get_by_id(db, item_id)
        if course is None or course.status.value != "active":
            return None
        return course.title, float(course.price or 0), {"webinar_id": course.id}
    bundle = await bundles_repo.get_active(db, item_id)
    if bundle is None:
        return None
    return bundle.title, float(bundle.price or 0), {"bundle_id": bundle.id}


def _read(gift: Gift) -> GiftRead:
    is_course = gift.webinar_id is not None
    return GiftRead(
        id=gift.id,
        item_type=GiftItemType.course if is_course else GiftItemType.bundle,
        item_id=gift.webinar_id if is_course else gift.bundle_id,
        name=gift.name,
        email=gift.email,
        description=gift.description,
        status=gift.status,
        viewed=gift.viewed,
        created_at=gift.created_at,
    )


@router.post(
    "/gifts",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_gift(payload: GiftCreate, current_user: CurrentUser, db: DbSession) -> OrderRead:
    """Gift a course/bundle to someone by email (legacy GiftController@store).

    Creates a pending Gift + order; settling it via /payments activates the gift
    and enrols the recipient if they already have an account."""
    resolved = await _resolve_item(db, payload.item_type, payload.item_id)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    title, price, item_fields = resolved
    if price <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_free")

    gift = await gifts_repo.create(
        db,
        Gift(
            user_id=current_user.id,
            name=payload.name,
            email=payload.email,
            description=payload.description,
            status=GiftStatus.pending,
            **item_fields,
        ),
    )
    order = await orders_repo.create(
        db,
        user_id=current_user.id,
        amount=price,
        total_discount=0,
        total_amount=price,
        items=[{"gift_id": gift.id, "amount": price, "total_amount": price}],
    )
    return order_read(order)


@router.get(
    "/panel/gifts/received",
    response_model=list[GiftRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def received_gifts(current_user: CurrentUser, db: DbSession) -> list[GiftRead]:
    """Active gifts addressed to my email."""
    if not current_user.email:
        return []
    rows = await gifts_repo.received_for_email(db, current_user.email)
    return [_read(g) for g in rows]


@router.get(
    "/panel/gifts/sent",
    response_model=list[GiftRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def sent_gifts(current_user: CurrentUser, db: DbSession) -> list[GiftRead]:
    rows = await gifts_repo.sent_by_user(db, current_user.id)
    return [_read(g) for g in rows]


@router.post(
    "/gifts/{gift_id}/redeem",
    response_model=GiftActionResponse,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def redeem_gift(gift_id: int, current_user: CurrentUser, db: DbSession) -> GiftActionResponse:
    """Redeem an active gift: enrol the recipient in the gifted item (idempotent)."""
    gift = await gifts_repo.get_by_id(db, gift_id)
    if gift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found")
    if gift.email != current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_recipient")
    if gift.status != GiftStatus.active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_active")

    course_ids = (
        [gift.webinar_id]
        if gift.webinar_id is not None
        else await bundles_repo.active_course_ids(db, gift.bundle_id)
        if gift.bundle_id is not None
        else []
    )
    for course_id in course_ids:
        if not await enrollments_repo.exists(db, user_id=current_user.id, course_id=course_id):
            await enrollments_repo.create(
                db, user_id=current_user.id, course_id=course_id, source=EnrollmentSource.gift
            )
    gift.viewed = True
    await db.commit()
    return GiftActionResponse(message="redeemed")
