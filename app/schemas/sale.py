from datetime import datetime

from pydantic import BaseModel

from app.models.order import PaymentMethod
from app.models.sale import SaleType


class SaleRead(BaseModel):
    id: int
    type: SaleType
    payment_method: PaymentMethod | None
    buyer_id: int
    seller_id: int | None
    order_id: int
    webinar_id: int | None
    bundle_id: int | None
    subscribe_id: int | None
    product_id: int | None
    amount: float
    discount: float | None
    total_amount: float
    created_at: datetime


class SellerSales(BaseModel):
    count: int
    total_income: float
    sales: list[SaleRead]
