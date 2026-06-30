from datetime import datetime

from pydantic import BaseModel, Field


class AccountBalance(BaseModel):
    """Wallet figures for the charge-account page (legacy getAccountingCharge)."""

    charge: float


class AccountingRead(BaseModel):
    """One financial-report row (legacy AccountingSummaryController list)."""

    id: int
    amount: float
    type: str  # addiction | deduction
    type_account: str
    description: str | None = None
    created_at: datetime


class OfflinePaymentRead(BaseModel):
    id: int
    bank: str | None = None
    reference_number: str | None = None
    amount: float
    status: str  # waiting | approved | reject
    attachment: str | None = None
    pay_date: datetime | None = None
    created_at: datetime


class OfflinePaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    bank: str | None = None
    reference_number: str | None = None
    pay_date: datetime | None = None
