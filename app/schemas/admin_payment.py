from datetime import datetime

from pydantic import BaseModel, Field

from app.models.payment import PaymentChannelStatus


class AdminPaymentChannelRead(BaseModel):
    id: int
    title: str
    class_name: str
    image: str | None
    status: PaymentChannelStatus
    test_mode: bool
    credentials: dict | None
    currencies: list | None
    created_at: datetime
    # Driver contract (legacy getCredentialItems / getShowTestModeToggle).
    credential_items: list[str]
    supported: bool
    show_test_mode_toggle: bool


class AdminPaymentChannelCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    class_name: str = Field(min_length=1, max_length=64)
    status: PaymentChannelStatus = PaymentChannelStatus.inactive
    test_mode: bool = False
    image: str | None = None
    credentials: dict | None = None
    currencies: list | None = None


class AdminPaymentChannelUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    image: str | None = None
    status: PaymentChannelStatus | None = None
    test_mode: bool | None = None
    credentials: dict | None = None
    currencies: list | None = None
