from datetime import datetime

from pydantic import BaseModel


class OrderItemRead(BaseModel):
    id: int
    course_id: int | None = None
    title: str | None = None
    slug: str | None = None
    amount: float
    discount: float | None = None
    total_amount: float


class OrderRead(BaseModel):
    id: int
    status: str
    amount: float  # sub_total
    total_discount: float | None = None
    tax: float | None = None
    total_amount: float
    created_at: datetime
    items: list[OrderItemRead] = []


class CheckoutRequest(BaseModel):
    discount_id: int | None = None
