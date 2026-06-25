"""Payment orchestration — parity of legacy PaymentsController + ChannelManager.

Real gateways (Stripe/Paypal/…) require per-deployment credentials and are wired
behind `PaymentChannel.class_name`; a built-in `Sandbox` driver completes payment
without external calls for dev/MVP. Marking an order paid grants course access
(wired in 4.5 via `_grant_access`).
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment, EnrollmentSource
from app.models.meeting import ReserveMeeting, ReserveStatus
from app.models.order import Order, OrderStatus, PaymentMethod
from app.models.payment import PaymentChannel
from app.models.sale import Sale
from app.models.subscription import UserSubscribe
from app.models.user import User
from app.repositories import bundles as bundles_repo
from app.repositories import enrollments as enrollments_repo
from app.repositories import orders as orders_repo
from app.services import email, sales
from app.services.payment_channels import make_channel


async def _enroll(db: AsyncSession, user_id: int, course_id: int, source: EnrollmentSource) -> None:
    """Enroll a buyer in a course (idempotent)."""
    if not await enrollments_repo.exists(db, user_id=user_id, course_id=course_id):
        db.add(Enrollment(user_id=user_id, course_id=course_id, source=source))


async def _grant_bundle(db: AsyncSession, user_id: int, bundle_id: int) -> None:
    """Enroll a buyer in every active course of a paid bundle (idempotent)."""
    for course_id in await bundles_repo.active_course_ids(db, bundle_id):
        await _enroll(db, user_id, course_id, EnrollmentSource.bundle)


def _grant_subscribe(db: AsyncSession, user_id: int, subscribe_id: int) -> None:
    """Activate a purchased subscription plan for the buyer (legacy
    createAccountingForSubscribe → UserSubscribe)."""
    db.add(UserSubscribe(user_id=user_id, subscribe_id=subscribe_id))


async def _confirm_reservation(db: AsyncSession, reserve_meeting_id: int, sale: Sale) -> None:
    """Link a paid reservation to its Sale and activate it (legacy
    setPaymentAccounting → reserve_meeting.sale_id + reserved_at)."""
    await db.flush()  # assign sale.id
    reservation = await db.get(ReserveMeeting, reserve_meeting_id)
    if reservation is not None:
        reservation.sale_id = sale.id
        reservation.reserved_at = datetime.now(UTC)
        reservation.status = ReserveStatus.open


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
        sale = await sales.record_sale(db, item, order.payment_method)
        if item.bundle_id is not None:
            await _grant_bundle(db, order.user_id, item.bundle_id)
        elif item.subscribe_id is not None:
            _grant_subscribe(db, order.user_id, item.subscribe_id)
        elif item.reserve_meeting_id is not None:
            await _confirm_reservation(db, item.reserve_meeting_id, sale)
        elif item.course_id is not None:
            await _enroll(db, order.user_id, item.course_id, EnrollmentSource.purchase)
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
