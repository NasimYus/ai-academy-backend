import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaymentChannelStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class PaymentChannel(Base):
    """A configured payment gateway, parity of legacy `payment_channels`.

    `class_name` selects the driver. Real gateways (Stripe/Paypal/…) need
    credentials and are wired per-deployment; a built-in `Sandbox` driver
    completes payments without external calls for dev/MVP.
    """

    __tablename__ = "payment_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    class_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[PaymentChannelStatus] = mapped_column(
        Enum(PaymentChannelStatus, name="payment_channel_status"),
        default=PaymentChannelStatus.active,
        nullable=False,
    )
    test_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image: Mapped[str | None] = mapped_column(String(512))
    # Per-deployment gateway credentials (merchant_id, api_key, …) as JSON.
    credentials: Mapped[dict | None] = mapped_column(JSONB)
    # Restrict the gateway to specific currency codes (null = any).
    currencies: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
