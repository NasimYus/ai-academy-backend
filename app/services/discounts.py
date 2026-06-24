"""Coupon validation + discount math — parity of Discount::checkValidDiscount
and CartController::handleDiscountPrice (course/category/all sources).

Deferred to later phases (treated as passing here): max-uses `count` and
`for_first_purchase` (need Orders/Sales — 4.3), user groups (Phase 5),
bundle/product/meeting/event sources (their phases).
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import CartItem
from app.models.discount import Discount, DiscountSource, DiscountType, DiscountUserType
from app.models.user import User
from app.repositories import discounts as discounts_repo

_COURSE_SOURCES = {DiscountSource.course, DiscountSource.category}
_UNSUPPORTED_SOURCES = {
    DiscountSource.bundle,
    DiscountSource.product,
    DiscountSource.meeting,
    DiscountSource.event,
    DiscountSource.meeting_package,
}


async def validate(
    db: AsyncSession, discount: Discount, user: User, items: list[CartItem], now: datetime
) -> str:
    """Return 'ok' or a reason code (legacy checkValidDiscount, course scope)."""
    if discount.expired_at is not None and discount.expired_at < now:
        return "expired"

    if discount.source in _UNSUPPORTED_SOURCES:
        return "wrong_items"  # cart holds only courses for now

    if discount.source in _COURSE_SOURCES and not items:
        return "not_for_courses"

    if discount.source == DiscountSource.course:
        scoped = await discounts_repo.course_ids(db, discount.id)
        if scoped and not any(i.course_id in scoped for i in items):
            return "wrong_course"

    if discount.source == DiscountSource.category:
        cats = await discounts_repo.category_ids(db, discount.id)
        if not any(i.course is not None and i.course.category_id in cats for i in items):
            return "wrong_category"

    if discount.user_type == DiscountUserType.special_users:
        if not await discounts_repo.user_whitelisted(db, discount.id, user.id):
            return "not_for_user"

    if discount.minimum_order:
        total = sum(float(i.course.price) for i in items if i.course)
        if discount.minimum_order > total:
            return "min_order"

    return "ok"


async def compute_discount(db: AsyncSession, discount: Discount, items: list[CartItem]) -> float:
    """Discount amount for the cart (legacy handleDiscountPrice)."""
    percent = discount.percent or 1

    if discount.source == DiscountSource.course:
        scoped = await discounts_repo.course_ids(db, discount.id)
        base = sum(float(i.course.price) for i in items if i.course and i.course_id in scoped)
    elif discount.source == DiscountSource.category:
        cats = await discounts_repo.category_ids(db, discount.id)
        base = sum(
            float(i.course.price) for i in items if i.course and i.course.category_id in cats
        )
    else:  # all
        base = sum(float(i.course.price) for i in items if i.course)

    if discount.discount_type == DiscountType.fixed_amount:
        amount = discount.amount or 0
        total_discount = float(amount if base > amount else base)
    else:
        total_discount = base * percent / 100 if base > 0 else 0.0
        if discount.max_amount and total_discount > discount.max_amount:
            total_discount = float(discount.max_amount)

    return total_discount
