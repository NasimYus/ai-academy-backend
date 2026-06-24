from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.discount import Discount
from app.repositories import cart as cart_repo
from app.repositories import orders as orders_repo
from app.schemas.common import error_responses
from app.schemas.order import CheckoutRequest, OrderRead, PurchaseRead
from app.services import discounts as discount_service
from app.services.order_presenter import order_read as _order_read

router = APIRouter(tags=["orders"])


@router.post(
    "/cart/checkout",
    response_model=OrderRead,
    responses=error_responses(status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED),
)
async def checkout(payload: CheckoutRequest, current_user: CurrentUser, db: DbSession) -> OrderRead:
    """Create a pending order from the cart, applying an optional coupon
    (legacy CartController@checkout + createOrderAndOrderItems). Payment is 4.4."""
    items = await cart_repo.list_for_user(db, current_user.id)
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_cart")

    discount: Discount | None = None
    if payload.discount_id is not None:
        candidate = await db.get(Discount, payload.discount_id)
        if candidate is not None:
            reason = await discount_service.validate(
                db, candidate, current_user, items, datetime.now(UTC)
            )
            if reason == "ok":
                discount = candidate

    sub_total = sum(float(i.course.price) for i in items if i.course)
    total_discount = 0.0
    if discount is not None:
        total_discount = await discount_service.compute_discount(db, discount, items)
        if total_discount > sub_total:
            total_discount = sub_total
    total = sub_total - total_discount

    order_items = []
    for i in items:
        price = float(i.course.price) if i.course else 0.0
        share = total_discount * price / sub_total if sub_total > 0 else 0.0
        order_items.append(
            {
                "course_id": i.course_id,
                "discount_id": discount.id if discount else None,
                "amount": price,
                "tax": 0,
                "commission": 0,
                "discount": share,
                "total_amount": price - share,
            }
        )

    order = await orders_repo.create(
        db,
        user_id=current_user.id,
        amount=sub_total,
        total_discount=total_discount,
        total_amount=total,
        items=order_items,
    )
    await cart_repo.clear(db, current_user.id)
    return _order_read(order)


@router.get(
    "/panel/orders",
    response_model=list[OrderRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def list_orders(current_user: CurrentUser, db: DbSession) -> list[OrderRead]:
    """The user's orders, newest first."""
    orders = await orders_repo.list_for_user(db, current_user.id)
    return [_order_read(o) for o in orders]


@router.get(
    "/panel/purchases",
    response_model=list[PurchaseRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def list_purchases(current_user: CurrentUser, db: DbSession) -> list[PurchaseRead]:
    """Buyer purchase history — paid course line-items (legacy indexPurchases)."""
    items = await orders_repo.paid_items_for_user(db, current_user.id)
    return [
        PurchaseRead(
            order_id=i.order_id,
            course_id=i.course_id,
            title=i.course.title if i.course else None,
            slug=i.course.slug if i.course else None,
            thumbnail=i.course.thumbnail if i.course else None,
            amount=float(i.total_amount),
            created_at=i.created_at,
        )
        for i in items
    ]


@router.get(
    "/panel/orders/{order_id}",
    response_model=OrderRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def get_order(order_id: int, current_user: CurrentUser, db: DbSession) -> OrderRead:
    order = await orders_repo.get_owned(db, order_id, current_user.id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return _order_read(order)
