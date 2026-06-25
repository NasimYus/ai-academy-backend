from typing import Literal

from pydantic import BaseModel


class PaymentChannelRead(BaseModel):
    id: int
    title: str
    class_name: str
    image: str | None = None
    # Credential keys this gateway needs (legacy getCredentialItems()).
    credential_items: list[str] = []
    supported: bool = True  # a driver is registered for this class_name


class PaymentRequestInput(BaseModel):
    order_id: int
    gateway_id: int


class PaymentRequestResult(BaseModel):
    order_id: int
    gateway: str
    status: str
    redirect_url: str


class PaymentVerifyInput(BaseModel):
    order_id: int
    status: Literal["success", "failed"] = "success"
