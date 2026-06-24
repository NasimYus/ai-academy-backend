from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.course import Course


class CartItem(Base):
    """A course queued for checkout, parity of legacy `cart` (course rows only).

    Legacy `cart` also carries bundle/product_order/reserve_meeting/ticket/
    special_offer references — those land with the store & meetings phases.
    """

    __tablename__ = "cart"
    __table_args__ = (UniqueConstraint("creator_id", "course_id", name="uq_cart_creator_course"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    course: Mapped["Course | None"] = relationship("Course", lazy="raise")
