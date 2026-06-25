import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.order import PaymentMethod


class SaleType(str, enum.Enum):
    webinar = "webinar"
    meeting = "meeting"
    subscribe = "subscribe"
    promotion = "promotion"
    registration_package = "registration_package"
    product = "product"
    bundle = "bundle"
    gift = "gift"
    installment_payment = "installment_payment"


class Sale(Base):
    """Accounting record for a paid order item — parity of legacy `sales`
    (Sale::createSales). One row per purchased item; carries buyer/seller,
    the typed item reference, and the resolved amounts."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    seller_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[SaleType] = mapped_column(Enum(SaleType, name="sale_type"), nullable=False)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method")
    )

    # Typed item references (exactly one set, per legacy createSales).
    webinar_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"))
    bundle_id: Mapped[int | None] = mapped_column(ForeignKey("bundles.id", ondelete="SET NULL"))
    subscribe_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscribes.id", ondelete="SET NULL")
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    reserve_meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("reserve_meetings.id", ondelete="SET NULL")
    )
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("meetings.id", ondelete="SET NULL"))
    meeting_time_id: Mapped[int | None] = mapped_column(
        ForeignKey("meeting_times.id", ondelete="SET NULL")
    )

    amount: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    tax: Mapped[float | None] = mapped_column(Numeric(15, 3))
    commission: Mapped[float | None] = mapped_column(Numeric(15, 3))
    discount: Mapped[float | None] = mapped_column(Numeric(15, 3))
    total_amount: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    refund_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
