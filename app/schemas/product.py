from datetime import datetime

from pydantic import BaseModel

from app.models.product import ProductStatus, ProductType

# Parity of legacy ProductResource (catalogue subset).


class ProductRead(BaseModel):
    id: int
    title: str
    thumbnail: str | None = None
    type: ProductType
    status: ProductStatus
    price: float | None = None
    point: int | None = None
    category_title: str | None = None
    category_id: int | None = None
    unlimited_inventory: bool = False
    inventory: int | None = None
    delivery_fee: float | None = None
    created_at: datetime


class ProductDetail(ProductRead):
    description: str | None = None


class ProductCategoryRead(BaseModel):
    id: int
    title: str
    icon: str | None = None
    sub_categories: list["ProductCategoryRead"] = []


class ProductCategoryList(BaseModel):
    count: int
    categories: list[ProductCategoryRead]
