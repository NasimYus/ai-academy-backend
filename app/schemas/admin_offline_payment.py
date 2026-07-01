from datetime import datetime

from pydantic import BaseModel


class AdminOfflinePaymentRead(BaseModel):
    id: int
    user_id: int
    user_name: str | None = None
    user_email: str | None = None
    bank: str | None = None
    reference_number: str | None = None
    amount: float
    status: str
    pay_date: datetime | None = None
    created_at: datetime
