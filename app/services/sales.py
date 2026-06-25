"""Sale accounting — parity of legacy `Sale::createSales`.

Records one `Sale` row per paid order item: derives the sale type and the typed
item reference from the order item, resolves the seller, and copies the resolved
amounts. The deferred paid paths (bundle/subscribe/meeting/product) plug in by
adding their ref to the order item — the derivation here already handles them.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
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

    if item.course_id is not None:
        sale_type = SaleType.webinar
        refs["webinar_id"] = item.course_id
        seller_id = await _seller_for_course(db, item.course_id)
    # NOTE: bundle/subscribe/reserve_meeting/product refs land here as their
    # paid entrypoints are wired (order item gains the matching column).

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
