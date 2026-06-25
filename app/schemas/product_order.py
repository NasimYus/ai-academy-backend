from datetime import datetime

from pydantic import BaseModel, Field

from app.models.product_order import ProductOrderStatus


class ProductOrderCreate(BaseModel):
    quantity: int = Field(default=1, ge=1)
    message_to_seller: str | None = None


class ProductOrderRead(BaseModel):
    id: int
    product_id: int
    title: str | None
    quantity: int
    status: ProductOrderStatus
    tracking_code: str | None
    created_at: datetime
