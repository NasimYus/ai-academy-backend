from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CartItemRead(BaseModel):
    id: int
    type: str  # "webinar" (course)
    course_id: int
    title: str
    slug: str
    thumbnail: str | None = None
    teacher_name: str | None = None
    price: float
    created_at: datetime


class CartAmounts(BaseModel):
    sub_total: float
    total_discount: float = 0
    tax_price: float = 0
    total: float


class CartRead(BaseModel):
    items: list[CartItemRead] = []
    amounts: CartAmounts


class AddToCartRequest(BaseModel):
    item_id: int
    # only courses are purchasable for now; bundle/product arrive with the store phase
    item_name: Literal["webinar"] = "webinar"


class CouponValidateRequest(BaseModel):
    coupon: str


class DiscountBrief(BaseModel):
    id: int
    title: str
    code: str
    discount_type: str
    percent: int | None = None
    amount: int | None = None


class CouponValidation(BaseModel):
    valid: bool
    message: str  # "valid" or a reason code (invalid/expired/min_order/…)
    amounts: CartAmounts | None = None
    discount: DiscountBrief | None = None
