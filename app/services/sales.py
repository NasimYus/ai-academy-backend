"""Sale accounting — parity of legacy `Sale::createSales`.

Records one `Sale` row per paid order item: derives the sale type and the typed
item reference from the order item, resolves the seller, and copies the resolved
amounts. The deferred paid paths (bundle/subscribe/meeting/product) plug in by
adding their ref to the order item — the derivation here already handles them.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bundle import Bundle
from app.models.course import Course
from app.models.meeting import Meeting, ReserveMeeting
from app.models.order import OrderItem, PaymentMethod
from app.models.sale import Sale, SaleType


async def _seller_for_course(db: AsyncSession, course_id: int) -> int | None:
    course = await db.get(Course, course_id)
    if course is None:
        return None
    return course.teacher_id or course.creator_id


async def record_sale(
    db: AsyncSession, item: OrderItem, payment_method: PaymentMethod | None
) -> Sale:
    """Create the Sale accounting row for one order item (does not commit)."""
    sale_type = SaleType.webinar
    seller_id: int | None = None
    refs: dict = {}

    if item.bundle_id is not None:
        sale_type = SaleType.bundle
        refs["bundle_id"] = item.bundle_id
        bundle = await db.get(Bundle, item.bundle_id)
        seller_id = bundle.creator_id if bundle else None
    elif item.subscribe_id is not None:
        # Subscriptions are sold by the platform (no instructor seller), per legacy.
        sale_type = SaleType.subscribe
        refs["subscribe_id"] = item.subscribe_id
    elif item.reserve_meeting_id is not None:
        sale_type = SaleType.meeting
        reservation = await db.get(ReserveMeeting, item.reserve_meeting_id)
        if reservation is not None:
            refs["reserve_meeting_id"] = reservation.id
            refs["meeting_id"] = reservation.meeting_id
            refs["meeting_time_id"] = reservation.meeting_time_id
            meeting = await db.get(Meeting, reservation.meeting_id)
            seller_id = meeting.creator_id if meeting else None
    elif item.course_id is not None:
        sale_type = SaleType.webinar
        refs["webinar_id"] = item.course_id
        seller_id = await _seller_for_course(db, item.course_id)
    # NOTE: reserve_meeting/product refs land here as their paid entrypoints
    # are wired (order item gains the matching column).

    sale = Sale(
        buyer_id=item.user_id,
        seller_id=seller_id,
        order_id=item.order_id,
        type=sale_type,
        payment_method=payment_method,
        amount=item.amount,
        tax=item.tax,
        commission=item.commission,
        discount=item.discount,
        total_amount=item.total_amount,
        **refs,
    )
    db.add(sale)
    return sale
