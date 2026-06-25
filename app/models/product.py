import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductType(str, enum.Enum):
    virtual = "virtual"
    physical = "physical"


class ProductStatus(str, enum.Enum):
    active = "active"
    pending = "pending"
    draft = "draft"
    inactive = "inactive"


class ProductCategory(Base):
    """Store product category, parity of `product_categories` (title inline)."""

    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(512))
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Product(Base):
    """A store product, parity of `products` (title/description inline).

    Reviews / comments / specifications / image gallery and purchasing
    (ProductOrder) are deferred — this slice covers the catalogue.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_categories.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    thumbnail: Mapped[str | None] = mapped_column(String(512))
    type: Mapped[ProductType] = mapped_column(
        Enum(ProductType, name="product_type"), default=ProductType.virtual, nullable=False
    )
    price: Mapped[float | None] = mapped_column(Numeric(15, 3))
    point: Mapped[int | None] = mapped_column(Integer)
    ordering: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlimited_inventory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    inventory: Mapped[int | None] = mapped_column(Integer)
    delivery_fee: Mapped[float | None] = mapped_column(Numeric(15, 3))
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"), default=ProductStatus.draft, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    category: Mapped[ProductCategory | None] = relationship("ProductCategory", lazy="raise")
