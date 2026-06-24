"""Payment orchestration — parity of legacy PaymentsController + ChannelManager.

Real gateways (Stripe/Paypal/…) require per-deployment credentials and are wired
behind `PaymentChannel.class_name`; a built-in `Sandbox` driver completes payment
without external calls for dev/MVP. Marking an order paid grants course access
(wired in 4.5 via `_grant_access`).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment, EnrollmentSource
from app.models.order import Order, OrderStatus, PaymentMethod
from app.models.payment import PaymentChannel
from app.repositories import enrollments as enrollments_repo


def build_redirect_url(order: Order, channel: PaymentChannel) -> str:
    """Where the gateway would send the user to pay. The Sandbox driver points
    back at the frontend callback which then POSTs /payments/verify."""
    return (
        f"/payment/callback?order_id={order.id}"
        f"&gateway={channel.class_name}&channel_id={channel.id}"
    )


async def start(db: AsyncSession, order: Order, channel: PaymentChannel) -> str:
    """Begin payment: mark the order `paying` and return the redirect URL."""
    order.payment_method = PaymentMethod.payment_channel
    order.status = OrderStatus.paying
    await db.commit()
    await db.refresh(order)
    return build_redirect_url(order, channel)


async def complete(db: AsyncSession, order: Order) -> None:
    """Mark an order paid and grant course access (legacy setPaymentAccounting →
    Sale rows). Each course item enrolls the buyer (idempotent)."""
    order.status = OrderStatus.paid
    for item in order.items:
        if item.course_id is None:
            continue
        if not await enrollments_repo.exists(db, user_id=order.user_id, course_id=item.course_id):
            db.add(
                Enrollment(
                    user_id=order.user_id,
                    course_id=item.course_id,
                    source=EnrollmentSource.purchase,
                )
            )
    await db.commit()
    await db.refresh(order)


async def fail(db: AsyncSession, order: Order) -> None:
    order.status = OrderStatus.fail
    await db.commit()
    await db.refresh(order)
