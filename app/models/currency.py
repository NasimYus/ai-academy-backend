from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

CURRENCY_POSITIONS = ("left", "right", "left_with_space", "right_with_space")
CURRENCY_SEPARATORS = ("dot", "comma")


class Currency(Base):
    """A display currency, parity of the legacy `currencies` table.

    Prices are stored in the default currency; `exchange_rate` converts a base
    price into this currency for display (`base * exchange_rate`).
    """

    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)  # ISO code, e.g. "USD"
    currency_position: Mapped[str] = mapped_column(String(20), default="left", nullable=False)
    currency_separator: Mapped[str] = mapped_column(String(8), default="dot", nullable=False)
    currency_decimal: Mapped[int | None] = mapped_column(Integer, default=0)
    exchange_rate: Mapped[float | None] = mapped_column(Float)
    order: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
