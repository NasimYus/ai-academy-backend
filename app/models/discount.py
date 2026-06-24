import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DiscountType(str, enum.Enum):
    percentage = "percentage"
    fixed_amount = "fixed_amount"


class DiscountUserType(str, enum.Enum):
    all_users = "all_users"
    special_users = "special_users"


class DiscountSource(str, enum.Enum):
    all = "all"
    course = "course"
    category = "category"
    bundle = "bundle"
    product = "product"
    meeting = "meeting"
    event = "event"
    meeting_package = "meeting_package"


class Discount(Base):
    """Coupon / discount code, parity of legacy `discounts`.

    Course-relevant fields only; functional sources are all/course/category
    (bundle/product/meeting/event arrive with their phases).
    """

    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    percent: Mapped[int | None] = mapped_column(Integer)
    amount: Mapped[int | None] = mapped_column(Integer)
    max_amount: Mapped[int | None] = mapped_column(Integer)
    minimum_order: Mapped[int | None] = mapped_column(Integer)
    count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    user_type: Mapped[DiscountUserType] = mapped_column(
        Enum(DiscountUserType, name="discount_user_type"),
        default=DiscountUserType.all_users,
        nullable=False,
    )
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, name="discount_type"), nullable=False
    )
    source: Mapped[DiscountSource] = mapped_column(
        Enum(DiscountSource, name="discount_source"), default=DiscountSource.all, nullable=False
    )
    for_first_purchase: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DiscountCourse(Base):
    """Scopes a course-source discount to specific courses (`discount_courses`)."""

    __tablename__ = "discount_courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    discount_id: Mapped[int] = mapped_column(
        ForeignKey("discounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )


class DiscountCategory(Base):
    """Scopes a category-source discount to specific categories (`discount_categories`)."""

    __tablename__ = "discount_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    discount_id: Mapped[int] = mapped_column(
        ForeignKey("discounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )


class DiscountUser(Base):
    """Whitelists users for a special_users discount (`discount_users`)."""

    __tablename__ = "discount_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    discount_id: Mapped[int] = mapped_column(
        ForeignKey("discounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
