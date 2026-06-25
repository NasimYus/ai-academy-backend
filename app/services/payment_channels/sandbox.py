from app.models.order import Order
from app.services.payment_channels.base import PaymentDriver


class SandboxChannel(PaymentDriver):
    """No-external-call gateway for dev/MVP: redirect to the SPA callback, which
    settles the order via /payments/verify with an explicit status."""

    class_name = "Sandbox"
    credential_items: list[str] = []

    def payment_request(self, order: Order) -> str:
        return self.callback_url(order)

    def verify(self, params: dict) -> bool:
        return params.get("status") == "success"
