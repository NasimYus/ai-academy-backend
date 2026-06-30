import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.bundle import Bundle
    from app.models.course import Course
    from app.models.meeting import ReserveMeeting
    from app.models.product import Product
    from app.models.subscription import Subscribe


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paying = "paying"
    paid = "paid"
    fail = "fail"


class PaymentMethod(str, enum.Enum):
    credit = "credit"
    payment_channel = "payment_channel"


class Order(Base):
    """A checkout order, parity of legacy `orders` (course items)."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.pending, nullable=False
    )
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method")
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)  # sub_total
    tax: Mapped[float | None] = mapped_column(Numeric(15, 3))
    total_discount: Mapped[float | None] = mapped_column(Numeric(15, 3))
    total_amount: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    reference_id: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", cascade="all, delete-orphan", lazy="raise"
    )


class OrderItem(Base):
    """A single course line in an order, parity of legacy `order_items`."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    bundle_id: Mapped[int | None] = mapped_column(ForeignKey("bundles.id", ondelete="SET NULL"))
    subscribe_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscribes.id", ondelete="SET NULL")
    )
    reserve_meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("reserve_meetings.id", ondelete="SET NULL")
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    product_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_orders.id", ondelete="SET NULL")
    )
    gift_id: Mapped[int | None] = mapped_column(ForeignKey("gifts.id", ondelete="SET NULL"))
    discount_id: Mapped[int | None] = mapped_column(ForeignKey("discounts.id", ondelete="SET NULL"))
    amount: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)  # item price
    tax: Mapped[float | None] = mapped_column(Numeric(15, 3))
    commission: Mapped[float | None] = mapped_column(Numeric(15, 3))
    discount: Mapped[float | None] = mapped_column(Numeric(15, 3))
    total_amount: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    course: Mapped["Course | None"] = relationship("Course", lazy="raise")
    bundle: Mapped["Bundle | None"] = relationship("Bundle", lazy="raise")
    subscribe: Mapped["Subscribe | None"] = relationship("Subscribe", lazy="raise")
    reserve_meeting: Mapped["ReserveMeeting | None"] = relationship("ReserveMeeting", lazy="raise")
    product: Mapped["Product | None"] = relationship("Product", lazy="raise")
