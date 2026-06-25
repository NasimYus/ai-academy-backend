from app.models.order import Order
from app.schemas.order import OrderItemRead, OrderRead


def order_read(order: Order) -> OrderRead:
    return OrderRead(
        id=order.id,
        status=order.status.value,
        amount=float(order.amount),
        total_discount=float(order.total_discount) if order.total_discount is not None else None,
        tax=float(order.tax) if order.tax is not None else None,
        total_amount=float(order.total_amount),
        created_at=order.created_at,
        items=[
            OrderItemRead(
                id=i.id,
                course_id=i.course_id,
                bundle_id=i.bundle_id,
                subscribe_id=i.subscribe_id,
                reserve_meeting_id=i.reserve_meeting_id,
                product_id=i.product_id,
                title=(
                    i.course.title
                    if i.course
                    else i.bundle.title
                    if i.bundle
                    else i.subscribe.title
                    if i.subscribe
                    else i.product.title
                    if i.product
                    else "Консультация"
                    if i.reserve_meeting_id
                    else None
                ),
                slug=i.course.slug if i.course else None,
                amount=float(i.amount),
                discount=float(i.discount) if i.discount is not None else None,
                total_amount=float(i.total_amount),
            )
            for i in order.items
        ],
    )
