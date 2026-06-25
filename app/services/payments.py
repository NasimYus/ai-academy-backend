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
from app.models.user import User
from app.repositories import enrollments as enrollments_repo
from app.repositories import orders as orders_repo
from app.services import email, sales
from app.services.payment_channels import make_channel


def build_redirect_url(order: Order, channel: PaymentChannel) -> str:
    """Resolve the channel's driver and build its payment redirect (legacy
    ChannelManager::makeChannel → paymentRequest)."""
    return make_channel(channel).payment_request(order)


async def start(db: AsyncSession, order: Order, channel: PaymentChannel) -> str:
    """Begin payment: mark the order `paying` and return the redirect URL."""
    order.payment_method = PaymentMethod.payment_channel
    order.status = OrderStatus.paying
    await db.commit()
    await db.refresh(order)
    return build_redirect_url(order, channel)


async def complete(db: AsyncSession, order: Order) -> None:
    """Mark an order paid, record Sale accounting rows, and grant access (legacy
    setPaymentAccounting → Sale::createSales). Each item gets a Sale; course
    items also enroll the buyer (idempotent)."""
    order.status = OrderStatus.paid
    for item in order.items:
        await sales.record_sale(db, item, order.payment_method)
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
    await _send_receipt(db, order)


async def _send_receipt(db: AsyncSession, order: Order) -> None:
    """Email a purchase receipt for a paid order (F.3)."""
    user = await db.get(User, order.user_id)
    if user is None or not user.email:
        return
    order = await orders_repo.reload(db, order.id)  # relationships expired after commit
    lines = [
        f"- {i.course.title if i.course else 'Курс'}: {float(i.total_amount)} TJS"
        for i in order.items
    ]
    body = (
        f"Спасибо за покупку! Заказ #{order.id} оплачен.\n\n"
        + "\n".join(lines)
        + f"\n\nИтого: {float(order.total_amount)} TJS\n\n"
        "Доступ к курсам уже открыт в разделе «Мои курсы»."
    )
    await email.send_email(
        to=user.email, subject=f"Чек по заказу #{order.id} — AI Academy", body=body
    )


async def fail(db: AsyncSession, order: Order) -> None:
    order.status = OrderStatus.fail
    await db.commit()
    await db.refresh(order)
