import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductOrderStatus(str, enum.Enum):
    pending = "pending"
    waiting_delivery = "waiting_delivery"
    shipped = "shipped"
    success = "success"
    canceled = "canceled"


class ProductOrder(Base):
    """A store product purchase, parity of legacy `product_orders`.

    Created pending at checkout; on paid the Sale is linked and the status
    advances (virtual → success; physical → waiting_delivery, per legacy)."""

    __tablename__ = "product_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    seller_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sale_id: Mapped[int | None] = mapped_column(ForeignKey("sales.id", ondelete="SET NULL"))
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    message_to_seller: Mapped[str | None] = mapped_column(Text)
    tracking_code: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[ProductOrderStatus] = mapped_column(
        Enum(ProductOrderStatus, name="product_order_status"),
        default=ProductOrderStatus.pending,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship("Product", lazy="raise")  # noqa: F821
